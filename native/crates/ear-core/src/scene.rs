use std::collections::VecDeque;

use crate::features::{FrameFeatures, analyze};
use crate::rhythm::RhythmMeter;
use crate::stft::{N_FFT, Spectrum, Stft};

const FLOOR_INIT: f32 = 0.004;
const FLOOR_DOWN: f32 = 0.1;
const FLOOR_RISE: f32 = 1.002;
const GATE_FACTOR: f32 = 3.2;
const GATE_MIN: f32 = 0.010;
const HISTORY: usize = 50;
const NOISE_RUN: usize = 10;
const NOISE_CAP: usize = 30;
const SPEECH_HOLD: usize = 14;
const BED_ALPHA: f32 = 0.985;
const BED_ON: f32 = 0.6;
const BED_OFF: f32 = 0.35;
const OVER_STRONG: f32 = 2.8;
const OVER_WEAK: f32 = 1.6;
const HARMONIC: f32 = 0.5;
const MOVING_CENTS: f32 = 12.0;
const STEADY_DB: f32 = 4.5;
const PAUSES: f32 = 0.1;
const BEAT_MIN: f32 = 0.3;
const BEAT_PAUSES: f32 = 0.06;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SoundKind {
    Silence,
    Speech,
    Music,
    Noise,
}

impl SoundKind {
    #[must_use]
    pub fn code(self) -> &'static str {
        match self {
            Self::Silence => "silence",
            Self::Speech => "speech",
            Self::Music => "music",
            Self::Noise => "noise",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct SceneVerdict {
    pub voiced: bool,
    pub kind: SoundKind,
    pub music_bed: bool,
    pub music_level: f32,
    pub floor: f32,
    pub harmonicity: f32,
    pub pitch_hz: f32,
}

#[derive(Debug, Clone, Copy)]
struct Past {
    level_db: f32,
    quiet: bool,
    pitch: f32,
}

#[derive(Debug)]
pub struct SceneClassifier {
    window: Vec<f32>,
    stft: Stft,
    spectrum: Spectrum,
    history: VecDeque<Past>,
    floor: f32,
    noise_run: usize,
    hold: usize,
    bed: f32,
    bed_on: bool,
    bed_power: f32,
    rhythm: RhythmMeter,
}

impl Default for SceneClassifier {
    fn default() -> Self {
        Self::new()
    }
}

fn mean(values: impl Iterator<Item = f32>) -> Option<f32> {
    let (sum, count) = values.fold((0.0_f32, 0_u32), |(s, c), v| (s + v, c.saturating_add(1)));
    if count == 0 {
        return None;
    }
    #[allow(clippy::cast_precision_loss)]
    let count = count as f32;
    Some(sum / count)
}

impl SceneClassifier {
    #[must_use]
    pub fn new() -> Self {
        Self {
            window: vec![0.0; N_FFT],
            stft: Stft::new(),
            spectrum: Stft::empty_spectrum(),
            history: VecDeque::with_capacity(HISTORY),
            floor: FLOOR_INIT,
            noise_run: 0,
            hold: 0,
            bed: 0.0,
            bed_on: false,
            bed_power: 0.0,
            rhythm: RhythmMeter::new(),
        }
    }

    pub fn reset_stream(&mut self) {
        self.window.iter_mut().for_each(|v| *v = 0.0);
        self.noise_run = 0;
        self.hold = 0;
        self.rhythm.reset();
    }

    #[must_use]
    pub fn floor(&self) -> f32 {
        self.floor
    }

    fn modulation_db(&self) -> f32 {
        let Some(avg) = mean(self.history.iter().map(|p| p.level_db)) else {
            return 0.0;
        };
        mean(self.history.iter().map(|p| (p.level_db - avg).powi(2)))
            .unwrap_or(0.0)
            .sqrt()
    }

    fn pause_ratio(&self) -> f32 {
        mean(self.history.iter().map(|p| if p.quiet { 1.0 } else { 0.0 })).unwrap_or(1.0)
    }

    fn pitch_motion(&self) -> Option<f32> {
        let pitches: Vec<f32> = self
            .history
            .iter()
            .rev()
            .take(17)
            .map(|p| p.pitch)
            .collect();
        let steps = pitches.windows(2).filter_map(|w| match w {
            [a, b] if *a > 0.0 && *b > 0.0 => Some((1200.0 * (a / b).log2()).abs()),
            _ => None,
        });
        let mut values: Vec<f32> = steps.collect();
        if values.len() < 4 {
            return None;
        }
        values.sort_by(f32::total_cmp);
        values.get(values.len() / 2).copied()
    }

    fn track_floor(&mut self, rms: f32) {
        if rms < self.floor {
            self.floor = self.floor * (1.0 - FLOOR_DOWN) + rms * FLOOR_DOWN;
        } else if !self.bed_on {
            self.floor *= FLOOR_RISE;
        }
        self.floor = self.floor.clamp(1e-5, 0.5);
    }

    fn remember(&mut self, f: &FrameFeatures, quiet: bool) {
        if self.history.len() >= HISTORY {
            self.history.pop_front();
        }
        let level_db = 20.0 * f.rms.max(1e-6).log10();
        let pitch = if f.harmonicity >= HARMONIC {
            f.pitch_hz
        } else {
            0.0
        };
        self.history.push_back(Past {
            level_db,
            quiet,
            pitch,
        });
    }

    fn beat_present(&self) -> bool {
        let reading = self.rhythm.read();
        reading.ready && reading.regularity >= BEAT_MIN && reading.pause_ratio < BEAT_PAUSES
    }

    fn music_evidence(&self, f: &FrameFeatures, moving: Option<f32>) -> f32 {
        let full = self.history.len() >= HISTORY;
        if !full {
            return 0.0;
        }
        let steady = self.modulation_db() < STEADY_DB;
        let continuous = self.pause_ratio() < PAUSES;
        let held = moving.is_some_and(|c| c < MOVING_CENTS);
        let tonal = f.harmonicity >= HARMONIC || f.flatness < 0.25;
        let votes = [steady, continuous, held, tonal]
            .iter()
            .filter(|v| **v)
            .count();
        match votes {
            4 => 1.0,
            3 if steady && continuous => 0.8,
            _ if self.beat_present() => 0.8,
            _ => 0.0,
        }
    }

    pub fn feed(&mut self, frame: &[f32]) -> SceneVerdict {
        self.window
            .extend(frame.iter().map(|v| if v.is_finite() { *v } else { 0.0 }));
        let excess = self.window.len().saturating_sub(N_FFT);
        self.window.drain(..excess);
        let f = analyze(frame, &self.window, &mut self.stft, &mut self.spectrum);
        let gate = (self.floor * GATE_FACTOR).max(GATE_MIN);
        let energetic = f.rms > gate;
        self.remember(&f, !energetic);
        self.rhythm.push(f.rms, !energetic);
        self.track_floor(f.rms);
        let moving = self.pitch_motion();
        let evidence = if energetic {
            self.music_evidence(&f, moving)
        } else {
            0.0
        };
        self.bed = BED_ALPHA * self.bed + (1.0 - BED_ALPHA) * evidence;
        if self.bed > BED_ON {
            self.bed_on = true;
        } else if self.bed < BED_OFF {
            self.bed_on = false;
        }
        let noise_like = energetic && f.harmonicity < 0.3 && f.flatness > 0.45;
        self.noise_run = if noise_like {
            self.noise_run.saturating_add(1).min(NOISE_CAP)
        } else if f.harmonicity >= HARMONIC || !energetic {
            0
        } else {
            self.noise_run.saturating_sub(1)
        };
        if self.bed_on && evidence > 0.0 {
            self.bed_power = if self.bed_power > 0.0 {
                0.95 * self.bed_power + 0.05 * f.band_power
            } else {
                f.band_power
            };
        }
        let over = f.band_power / self.bed_power.max(1e-12);
        let pitch_moving = moving.is_some_and(|c| c >= MOVING_CENTS);
        let speech_over_bed =
            over > OVER_STRONG || (over > OVER_WEAK && f.harmonicity >= HARMONIC && pitch_moving);
        let kind = if !energetic {
            SoundKind::Silence
        } else if self.bed_on && !speech_over_bed {
            SoundKind::Music
        } else if self.noise_run >= NOISE_RUN && self.hold == 0 {
            SoundKind::Noise
        } else {
            SoundKind::Speech
        };
        if kind == SoundKind::Speech && f.harmonicity >= HARMONIC {
            self.hold = SPEECH_HOLD;
        } else {
            self.hold = self.hold.saturating_sub(1);
        }
        SceneVerdict {
            voiced: kind == SoundKind::Speech,
            kind,
            music_bed: self.bed_on,
            music_level: self.bed,
            floor: self.floor,
            harmonicity: f.harmonicity,
            pitch_hz: f.pitch_hz,
        }
    }
}
