use crate::mel::Frame;

pub const GATE_DB: f32 = 9.0;
const FALL: f32 = 0.9;
const RISE: f32 = 0.001;
const MIN_DB: f32 = -90.0;
const TRIM_PAD: usize = 3;
const TRIM_DB: f32 = 10.0;
const MIN_PEAK_DB: f32 = -50.0;
const MIN_CONTRAST_DB: f32 = 12.0;

#[derive(Debug, Clone, Copy)]
pub struct NoiseFloor {
    level: f32,
    primed: bool,
}

impl Default for NoiseFloor {
    fn default() -> Self {
        Self {
            level: MIN_DB,
            primed: false,
        }
    }
}

impl NoiseFloor {
    pub fn update(&mut self, energy_db: f32) {
        let e = energy_db.max(MIN_DB);
        if !self.primed {
            self.level = e;
            self.primed = true;
        } else if e < self.level {
            self.level = self.level * FALL + e * (1.0 - FALL);
        } else {
            self.level += RISE * (e - self.level);
        }
    }

    #[must_use]
    pub fn is_speech(self, energy_db: f32) -> bool {
        self.primed && energy_db > self.level + GATE_DB
    }
}

#[must_use]
pub fn trim(frames: &[Frame]) -> Option<(usize, usize)> {
    if frames.len() < 8 {
        return None;
    }
    let mut sorted: Vec<f32> = frames.iter().map(|f| f.energy_db).collect();
    sorted.sort_by(f32::total_cmp);
    let floor = sorted.get(sorted.len() / 10).copied()?;
    let peak = sorted.last().copied()?;
    if peak < MIN_PEAK_DB || peak - floor < MIN_CONTRAST_DB {
        return None;
    }
    let gate = (floor + TRIM_DB).min(peak - 3.0);
    let first = frames.iter().position(|f| f.energy_db > gate)?;
    let last = frames.iter().rposition(|f| f.energy_db > gate)?;
    let start = first.saturating_sub(TRIM_PAD);
    let end = last
        .saturating_add(TRIM_PAD)
        .saturating_add(1)
        .min(frames.len());
    (end > start).then_some((start, end))
}
