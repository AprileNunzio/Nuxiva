use std::collections::VecDeque;

pub const WINDOW_FRAMES: usize = 300;
pub const MIN_FRAMES: usize = 180;
const LAG_MIN: usize = 10;
const LAG_MAX: usize = 34;

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct RhythmReading {
    pub ready: bool,
    pub regularity: f32,
    pub pause_ratio: f32,
}

#[derive(Debug, Clone, Default)]
pub struct RhythmMeter {
    levels: VecDeque<f32>,
    quiet: VecDeque<bool>,
}

impl RhythmMeter {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    pub fn reset(&mut self) {
        self.levels.clear();
        self.quiet.clear();
    }

    pub fn push(&mut self, rms: f32, quiet: bool) {
        let level = if rms.is_finite() {
            rms.max(1e-6).ln()
        } else {
            1e-6_f32.ln()
        };
        if self.levels.len() >= WINDOW_FRAMES {
            self.levels.pop_front();
            self.quiet.pop_front();
        }
        self.levels.push_back(level);
        self.quiet.push_back(quiet);
    }

    #[must_use]
    pub fn read(&self) -> RhythmReading {
        let count = self.levels.len();
        if count < MIN_FRAMES {
            return RhythmReading {
                ready: false,
                regularity: 0.0,
                pause_ratio: 1.0,
            };
        }
        #[allow(clippy::cast_precision_loss)]
        let total = count as f32;
        let pauses = self.quiet.iter().filter(|q| **q).count();
        #[allow(clippy::cast_precision_loss)]
        let pause_ratio = pauses as f32 / total;
        RhythmReading {
            ready: true,
            regularity: self.regularity(),
            pause_ratio,
        }
    }

    fn onsets(&self) -> Vec<f32> {
        let levels: Vec<f32> = self.levels.iter().copied().collect();
        let raw: Vec<f32> = levels
            .windows(2)
            .map(|w| match w {
                [a, b] => (b - a).max(0.0),
                _ => 0.0,
            })
            .collect();
        #[allow(clippy::cast_precision_loss)]
        let mean = raw.iter().sum::<f32>() / raw.len().max(1) as f32;
        raw.iter().map(|v| v - mean).collect()
    }

    fn regularity(&self) -> f32 {
        let onsets = self.onsets();
        let energy: f32 = onsets.iter().map(|v| v * v).sum();
        if energy < 1e-6 {
            return 0.0;
        }
        let mut best = 0.0_f32;
        for lag in LAG_MIN..=LAG_MAX {
            let Some(tail) = onsets.get(lag..) else {
                break;
            };
            let cross: f32 = onsets.iter().zip(tail).map(|(a, b)| a * b).sum();
            #[allow(clippy::cast_precision_loss)]
            let scale = onsets.len() as f32 / onsets.len().saturating_sub(lag).max(1) as f32;
            best = best.max(cross * scale / energy);
        }
        best.clamp(0.0, 1.0)
    }
}
