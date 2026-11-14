use serde::{Deserialize, Serialize};

use crate::error::{BenchError, BenchResult};
use crate::scene::Background;
use crate::stats::{ratio, round3, u64_f64};

pub const MAX_TRIAL_AUDIO_MS: u64 = 3_600_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct WakeTrial {
    pub expect_wake: bool,
    pub fired: bool,
    pub audio_ms: u64,
    pub background: Background,
}

impl WakeTrial {
    pub fn validate(&self) -> BenchResult<()> {
        if self.audio_ms == 0 || self.audio_ms > MAX_TRIAL_AUDIO_MS {
            return Err(BenchError::Invalid("wake_audio_ms"));
        }
        Ok(())
    }
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct WakeReport {
    pub trials: u64,
    pub positives: u64,
    pub negatives: u64,
    pub negative_hours: f64,
    pub background_negative_hours: f64,
    pub missed: u64,
    pub false_accepts: u64,
    pub background_false_accepts: u64,
    pub miss_rate: f64,
    pub false_accepts_per_hour: f64,
    pub background_false_accepts_per_hour: f64,
}

fn per_hour(events: u64, audio_ms: u64) -> f64 {
    if audio_ms == 0 {
        0.0
    } else {
        round3(u64_f64(events) * 3_600_000.0 / u64_f64(audio_ms))
    }
}

pub fn analyze(trials: &[WakeTrial]) -> BenchResult<WakeReport> {
    let mut r = WakeReport::default();
    let mut negative_ms = 0u64;
    let mut background_ms = 0u64;
    for t in trials {
        t.validate()?;
        r.trials = r.trials.saturating_add(1);
        if t.expect_wake {
            r.positives = r.positives.saturating_add(1);
            if !t.fired {
                r.missed = r.missed.saturating_add(1);
            }
            continue;
        }
        r.negatives = r.negatives.saturating_add(1);
        negative_ms = negative_ms.saturating_add(t.audio_ms);
        if t.fired {
            r.false_accepts = r.false_accepts.saturating_add(1);
        }
        if t.background.is_noisy() {
            background_ms = background_ms.saturating_add(t.audio_ms);
            if t.fired {
                r.background_false_accepts = r.background_false_accepts.saturating_add(1);
            }
        }
    }
    r.negative_hours = round3(u64_f64(negative_ms) / 3_600_000.0);
    r.background_negative_hours = round3(u64_f64(background_ms) / 3_600_000.0);
    r.miss_rate = ratio(r.missed, r.positives);
    r.false_accepts_per_hour = per_hour(r.false_accepts, negative_ms);
    r.background_false_accepts_per_hour = per_hour(r.background_false_accepts, background_ms);
    Ok(r)
}
