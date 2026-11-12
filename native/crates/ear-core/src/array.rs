use std::collections::VecDeque;
use std::fmt;

use crate::align::{ALIGN_WINDOW, Aligner, MAX_LAG};

pub const MAX_CHANNELS: usize = 8;
pub const MAX_ARRAY_FRAME: usize = 4_800;
const HISTORY: usize = ALIGN_WINDOW + MAX_ARRAY_FRAME + 2 * MAX_LAG;
const ALIGN_EVERY: u32 = 12;
const SWITCH_DB: f32 = 3.0;
const SWITCH_FRAMES: u32 = 10;
const FUSE_DB: f32 = 6.0;
const MIN_COHERENCE: f32 = 0.45;
const DEAD_RMS: f32 = 1e-5;
const DEAD_FRAMES: u32 = 50;
const DEAD_SCORE: f32 = -100.0;
const CLIP_LEVEL: f32 = 0.98;
const CLIP_PENALTY_DB: f32 = 60.0;
const SPEECH_RATIO: f32 = 2.0;
const FLOOR_FALL: f32 = 0.9;
const FLOOR_RISE: f32 = 1.005;
const LEVEL_SMOOTH: f32 = 0.92;
const CLIP_SMOOTH: f32 = 0.95;
const FLOOR_MIN: f32 = 1e-6;
const GAIN_MIN: f32 = 0.25;
const GAIN_MAX: f32 = 4.0;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ArrayError {
    ChannelCount,
    FrameLength,
}

impl fmt::Display for ArrayError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(match self {
            Self::ChannelCount => "ear.array.channels",
            Self::FrameLength => "ear.array.frame",
        })
    }
}

impl std::error::Error for ArrayError {}

#[derive(Debug, Clone, PartialEq)]
pub struct ArrayFrame {
    pub samples: Vec<f32>,
    pub best: usize,
    pub fused: usize,
    pub scores: Vec<f32>,
}

#[derive(Debug, Clone)]
struct Channel {
    history: VecDeque<f32>,
    floor: f32,
    level: f32,
    clip: f32,
    quiet: u32,
    primed: bool,
    lag: Option<isize>,
    coherence: f32,
}

impl Channel {
    fn new() -> Self {
        Self {
            history: std::iter::repeat_n(0.0, HISTORY).collect(),
            floor: 0.003,
            level: 0.003,
            clip: 0.0,
            quiet: 0,
            primed: false,
            lag: None,
            coherence: 0.0,
        }
    }

    fn push(&mut self, frame: &[f32]) {
        let rms = frame_rms(frame);
        if !self.primed {
            self.primed = true;
            self.floor = rms.max(FLOOR_MIN);
            self.level = self.floor;
        } else if rms < self.floor {
            self.floor = (self.floor * FLOOR_FALL + rms * (1.0 - FLOOR_FALL)).max(FLOOR_MIN);
        } else {
            self.floor = (self.floor * FLOOR_RISE).max(FLOOR_MIN);
        }
        if rms > self.floor * SPEECH_RATIO {
            self.level = self.level * LEVEL_SMOOTH + rms * (1.0 - LEVEL_SMOOTH);
        }
        let clipped = share(
            frame.iter().filter(|v| v.abs() >= CLIP_LEVEL).count(),
            frame.len(),
        );
        self.clip = self.clip * CLIP_SMOOTH + clipped * (1.0 - CLIP_SMOOTH);
        self.quiet = if rms < DEAD_RMS {
            self.quiet.saturating_add(1)
        } else {
            0
        };
        for v in frame {
            self.history.push_back(if v.is_finite() { *v } else { 0.0 });
        }
        while self.history.len() > HISTORY {
            self.history.pop_front();
        }
    }

    fn score(&self) -> f32 {
        if self.quiet >= DEAD_FRAMES {
            return DEAD_SCORE;
        }
        let snr =
            20.0 * ((self.level.max(self.floor) + FLOOR_MIN) / (self.floor + FLOOR_MIN)).log10();
        snr - self.clip * CLIP_PENALTY_DB
    }

    fn window(&self, end_back: usize, len: usize) -> Vec<f32> {
        let end = self.history.len().saturating_sub(end_back);
        let start = end.saturating_sub(len);
        self.history.range(start..end).copied().collect()
    }

    fn voiced(&self) -> bool {
        self.level > self.floor * SPEECH_RATIO
    }
}

fn frame_rms(frame: &[f32]) -> f32 {
    if frame.is_empty() {
        return 0.0;
    }
    let sum: f64 = frame.iter().map(|v| f64::from(*v) * f64::from(*v)).sum();
    #[allow(clippy::cast_precision_loss, clippy::cast_possible_truncation)]
    let value = (sum / frame.len() as f64).sqrt() as f32;
    value
}

fn share(count: usize, total: usize) -> f32 {
    if total == 0 {
        return 0.0;
    }
    #[allow(clippy::cast_precision_loss)]
    let value = count as f32 / total as f32;
    value
}

#[must_use]
pub fn pick_best(scores: &[f32], current: usize, streak: &mut (usize, u32)) -> usize {
    let current_score = scores.get(current).copied().unwrap_or(DEAD_SCORE);
    let leader = scores
        .iter()
        .enumerate()
        .max_by(|a, b| a.1.total_cmp(b.1))
        .map_or(current, |(i, _)| i);
    let leader_score = scores.get(leader).copied().unwrap_or(DEAD_SCORE);
    if current_score <= DEAD_SCORE && leader_score > DEAD_SCORE {
        *streak = (leader, 0);
        return leader;
    }
    if leader == current || leader_score < current_score + SWITCH_DB {
        *streak = (current, 0);
        return current;
    }
    if streak.0 == leader {
        streak.1 = streak.1.saturating_add(1);
    } else {
        *streak = (leader, 1);
    }
    if streak.1 >= SWITCH_FRAMES {
        *streak = (leader, 0);
        return leader;
    }
    current
}

pub struct MicArray {
    channels: Vec<Channel>,
    aligner: Aligner,
    best: usize,
    streak: (usize, u32),
    frames: u32,
}

impl fmt::Debug for MicArray {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("MicArray")
            .field("channels", &self.channels.len())
            .field("best", &self.best)
            .finish_non_exhaustive()
    }
}

impl MicArray {
    pub fn new(channels: usize) -> Result<Self, ArrayError> {
        if channels == 0 || channels > MAX_CHANNELS {
            return Err(ArrayError::ChannelCount);
        }
        Ok(Self {
            channels: (0..channels).map(|_| Channel::new()).collect(),
            aligner: Aligner::new(),
            best: 0,
            streak: (0, 0),
            frames: 0,
        })
    }

    #[must_use]
    pub fn channels(&self) -> usize {
        self.channels.len()
    }

    #[must_use]
    pub fn best(&self) -> usize {
        self.best
    }

    pub fn reset(&mut self) {
        let count = self.channels.len();
        self.channels = (0..count).map(|_| Channel::new()).collect();
        self.best = 0;
        self.streak = (0, 0);
        self.frames = 0;
    }

    pub fn mix(&mut self, frames: &[&[f32]]) -> Result<ArrayFrame, ArrayError> {
        if frames.len() != self.channels.len() {
            return Err(ArrayError::ChannelCount);
        }
        let len = frames.first().map_or(0, |f| f.len());
        if len == 0 || len > MAX_ARRAY_FRAME || frames.iter().any(|f| f.len() != len) {
            return Err(ArrayError::FrameLength);
        }
        for (channel, frame) in self.channels.iter_mut().zip(frames) {
            channel.push(frame);
        }
        let scores: Vec<f32> = self.channels.iter().map(Channel::score).collect();
        let previous = self.best;
        self.best = pick_best(&scores, previous, &mut self.streak);
        if self.best != previous {
            self.channels.iter_mut().for_each(|c| c.lag = None);
        }
        self.frames = self.frames.wrapping_add(1);
        if self.frames % ALIGN_EVERY == 0 {
            self.align(&scores);
        }
        let fresh = self.render(self.best, &scores, len);
        let samples = if self.best == previous {
            fresh
        } else {
            let old = self.render_single(previous, len);
            crossfade(&old, &fresh)
        };
        let fused = self.members(self.best, &scores).len();
        Ok(ArrayFrame {
            samples,
            best: self.best,
            fused,
            scores,
        })
    }

    fn align(&mut self, scores: &[f32]) {
        let best = self.best;
        let Some(reference) = self.channels.get(best) else {
            return;
        };
        if !reference.voiced() {
            return;
        }
        let best_score = scores.get(best).copied().unwrap_or(DEAD_SCORE);
        let ref_window = reference.window(0, ALIGN_WINDOW);
        for index in 0..self.channels.len() {
            if index == best {
                continue;
            }
            let score = scores.get(index).copied().unwrap_or(DEAD_SCORE);
            let Some(channel) = self.channels.get(index) else {
                continue;
            };
            if score < best_score - FUSE_DB || !channel.voiced() {
                continue;
            }
            let window = channel.window(0, ALIGN_WINDOW);
            let estimate = self.aligner.estimate(&ref_window, &window);
            if let (Some(found), Some(channel)) = (estimate, self.channels.get_mut(index)) {
                channel.lag = Some(found.lag);
                channel.coherence = found.coherence;
            }
        }
    }

    fn members(&self, best: usize, scores: &[f32]) -> Vec<(usize, isize)> {
        let best_score = scores.get(best).copied().unwrap_or(DEAD_SCORE);
        let mut out = vec![(best, 0_isize)];
        for (index, channel) in self.channels.iter().enumerate() {
            if index == best {
                continue;
            }
            let score = scores.get(index).copied().unwrap_or(DEAD_SCORE);
            if let Some(lag) = channel.lag {
                if channel.coherence >= MIN_COHERENCE
                    && score >= best_score - FUSE_DB
                    && score > DEAD_SCORE
                {
                    out.push((index, lag));
                }
            }
        }
        out
    }

    fn render_single(&self, index: usize, len: usize) -> Vec<f32> {
        self.channels
            .get(index)
            .map_or_else(|| vec![0.0; len], |c| c.window(MAX_LAG, len))
    }

    fn render(&self, best: usize, scores: &[f32], len: usize) -> Vec<f32> {
        let members = self.members(best, scores);
        if members.len() < 2 {
            return self.render_single(best, len);
        }
        let ref_level = self
            .channels
            .get(best)
            .map_or(1.0, |c| c.level.max(FLOOR_MIN));
        let weights: Vec<f32> = members
            .iter()
            .map(|(i, _)| {
                10_f32.powf(scores.get(*i).copied().unwrap_or(0.0).clamp(-40.0, 60.0) / 20.0)
            })
            .collect();
        let total: f32 = weights.iter().sum::<f32>().max(FLOOR_MIN);
        let mut out = vec![0.0_f32; len];
        for ((index, lag), weight) in members.iter().zip(&weights) {
            let Some(channel) = self.channels.get(*index) else {
                continue;
            };
            let gain = (ref_level / channel.level.max(FLOOR_MIN)).clamp(GAIN_MIN, GAIN_MAX);
            let back = if *lag >= 0 {
                MAX_LAG.saturating_sub(lag.unsigned_abs())
            } else {
                MAX_LAG.saturating_add(lag.unsigned_abs())
            };
            let part = channel.window(back, len);
            let scale = weight / total * gain;
            for (slot, v) in out.iter_mut().zip(part.iter()) {
                *slot += v * scale;
            }
        }
        for v in &mut out {
            *v = v.clamp(-1.0, 1.0);
        }
        out
    }
}

fn crossfade(old: &[f32], new: &[f32]) -> Vec<f32> {
    let n = new.len().max(1);
    #[allow(clippy::cast_precision_loss)]
    let step = 1.0 / n as f32;
    old.iter()
        .zip(new.iter())
        .enumerate()
        .map(|(i, (a, b))| {
            #[allow(clippy::cast_precision_loss)]
            let t = i as f32 * step;
            a * (1.0 - t) + b * t
        })
        .collect()
}
