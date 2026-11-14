#![allow(clippy::indexing_slicing, clippy::arithmetic_side_effects)]

use std::collections::VecDeque;

use crate::dtw;
use crate::error::{WakeError, WakeResult};
use crate::mel::{self, Ceps, Feat, Frame, Frontend, HOP, RATE, WIN};
use crate::model::{MAX_FRAMES, MIN_FRAMES, Model};
use crate::vad::NoiseFloor;

const RING_SAMPLES: usize = RATE * 3;
const FRAME_CAP: usize = 320;
const EVAL_EVERY: usize = 8;
const SETTLE: u8 = 2;
const SPEECH_SHARE: f32 = 0.55;
const PREROLL: usize = RATE / 5;
const RATIOS: [f32; 5] = [0.75, 0.88, 1.0, 1.14, 1.3];
const MIN_SENSITIVITY: f32 = 0.5;
const MAX_SENSITIVITY: f32 = 1.6;

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Config {
    pub sensitivity: f32,
    pub refractory_ms: u32,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            sensitivity: 1.0,
            refractory_ms: 1500,
        }
    }
}

impl Config {
    pub fn validate(self) -> WakeResult<Self> {
        if self.sensitivity.is_finite()
            && (MIN_SENSITIVITY..=MAX_SENSITIVITY).contains(&self.sensitivity)
            && (200..=10_000).contains(&self.refractory_ms)
        {
            Ok(self)
        } else {
            Err(WakeError::Config)
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct Detection {
    pub confidence: f32,
    pub distance: f32,
    pub pcm: Vec<i16>,
}

#[derive(Debug, Clone, Copy)]
struct Tracked {
    ceps: Ceps,
    speech: bool,
}

#[derive(Debug)]
struct Pending {
    distance: f32,
    pcm: Vec<i16>,
    age: u8,
}

#[derive(Debug)]
pub struct Detector {
    model: Model,
    config: Config,
    front: Frontend,
    floor: NoiseFloor,
    buffer: Vec<f32>,
    ring: VecDeque<i16>,
    frames: VecDeque<Tracked>,
    since_eval: usize,
    cooldown: usize,
    pending: Option<Pending>,
}

impl Detector {
    pub fn new(model: Model, config: Config) -> WakeResult<Self> {
        Ok(Self {
            model,
            config: config.validate()?,
            front: Frontend::new(),
            floor: NoiseFloor::default(),
            buffer: Vec::new(),
            ring: VecDeque::with_capacity(RING_SAMPLES),
            frames: VecDeque::with_capacity(FRAME_CAP),
            since_eval: 0,
            cooldown: 0,
            pending: None,
        })
    }

    pub fn reset(&mut self) {
        self.floor = NoiseFloor::default();
        self.buffer.clear();
        self.ring.clear();
        self.frames.clear();
        self.since_eval = 0;
        self.cooldown = 0;
        self.pending = None;
    }

    pub fn push(&mut self, pcm: &[i16]) -> Vec<Detection> {
        let mut found = Vec::new();
        for &s in pcm {
            if self.ring.len() >= RING_SAMPLES {
                self.ring.pop_front();
            }
            self.ring.push_back(s);
            self.buffer.push(f32::from(s) / 32768.0);
            if self.buffer.len() >= WIN {
                self.step(&mut found);
            }
        }
        found
    }

    fn step(&mut self, found: &mut Vec<Detection>) {
        let frame: Option<Frame> = self.buffer.get(..WIN).and_then(|w| self.front.frame(w));
        self.buffer.drain(..HOP);
        let Some(frame) = frame else { return };
        self.floor.update(frame.energy_db);
        if self.frames.len() >= FRAME_CAP {
            self.frames.pop_front();
        }
        self.frames.push_back(Tracked {
            ceps: frame.ceps,
            speech: self.floor.is_speech(frame.energy_db),
        });
        self.cooldown = self.cooldown.saturating_sub(1);
        self.since_eval += 1;
        if self.since_eval < EVAL_EVERY {
            return;
        }
        self.since_eval = 0;
        if self.cooldown > 0 {
            self.pending = None;
            return;
        }
        self.evaluate(found);
    }

    fn effective_threshold(&self) -> f32 {
        self.model.threshold() * self.config.sensitivity
    }

    fn best_window(&self) -> Option<(f32, usize)> {
        let threshold = self.effective_threshold();
        let reference = self.model.reference_frames() as f32;
        let mut best: Option<(f32, usize)> = None;
        for ratio in RATIOS {
            let len = ((reference * ratio).round() as usize).clamp(MIN_FRAMES, MAX_FRAMES);
            if len > self.frames.len() {
                continue;
            }
            let window: Vec<&Tracked> = self.frames.iter().rev().take(len).collect();
            let voiced = window.iter().filter(|t| t.speech).count();
            if (voiced as f32) < SPEECH_SHARE * len as f32 {
                continue;
            }
            let ceps: Vec<Ceps> = window.iter().rev().map(|t| t.ceps).collect();
            let feats: Vec<Feat> = mel::features(&ceps);
            let bound = best.map_or(threshold, |(d, _)| d.min(threshold));
            for template in self.model.templates() {
                if let Some(d) = dtw::distance(&feats, template, bound) {
                    if d <= threshold && best.is_none_or(|(b, _)| d < b) {
                        best = Some((d, len));
                    }
                }
            }
        }
        best
    }

    fn snapshot(&self, frames: usize) -> Vec<i16> {
        let want = frames
            .saturating_mul(HOP)
            .saturating_add(WIN)
            .saturating_add(PREROLL);
        let usable = self.ring.len().saturating_sub(self.buffer.len());
        let take = want.min(usable);
        let skip = usable.saturating_sub(take);
        self.ring.iter().skip(skip).take(take).copied().collect()
    }

    fn evaluate(&mut self, found: &mut Vec<Detection>) {
        match self.best_window() {
            Some((distance, len)) => {
                let better = self.pending.as_ref().is_none_or(|p| distance < p.distance);
                if better {
                    self.pending = Some(Pending {
                        distance,
                        pcm: self.snapshot(len),
                        age: 0,
                    });
                } else if let Some(p) = self.pending.as_mut() {
                    p.age = p.age.saturating_add(1);
                }
            }
            None => {
                if let Some(p) = self.pending.as_mut() {
                    p.age = p.age.saturating_add(1);
                }
            }
        }
        if self.pending.as_ref().is_some_and(|p| p.age >= SETTLE) {
            if let Some(p) = self.pending.take() {
                let threshold = self.effective_threshold();
                found.push(Detection {
                    confidence: (1.0 - p.distance / (2.0 * threshold)).clamp(0.0, 1.0),
                    distance: p.distance,
                    pcm: p.pcm,
                });
                self.cooldown = (self.config.refractory_ms as usize) / 10;
            }
        }
    }
}
