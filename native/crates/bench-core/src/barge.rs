use serde::{Deserialize, Serialize};

use crate::error::{BenchError, BenchResult};
use crate::latency::MAX_STAGE_MS;
use crate::scene::Background;
use crate::stats::{Summary, ratio, summarize};

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct BargeTrial {
    pub expect_barge: bool,
    pub fired: bool,
    pub reaction_ms: Option<f64>,
    pub background: Background,
}

impl BargeTrial {
    pub fn validate(&self) -> BenchResult<()> {
        match self.reaction_ms {
            Some(v) if !v.is_finite() || !(0.0..=MAX_STAGE_MS).contains(&v) => {
                Err(BenchError::Invalid("barge_reaction_ms"))
            }
            Some(_) if !self.fired => Err(BenchError::Invalid("barge_reaction_without_fire")),
            _ => Ok(()),
        }
    }
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct BargeReport {
    pub trials: u64,
    pub positives: u64,
    pub negatives: u64,
    pub detected: u64,
    pub false_barges: u64,
    pub background_false_barges: u64,
    pub background_negatives: u64,
    pub miss_rate: f64,
    pub false_rate: f64,
    pub background_false_rate: f64,
    pub reaction: Summary,
}

pub fn analyze(trials: &[BargeTrial]) -> BenchResult<BargeReport> {
    let mut r = BargeReport::default();
    let mut reactions = Vec::new();
    for t in trials {
        t.validate()?;
        r.trials = r.trials.saturating_add(1);
        if t.expect_barge {
            r.positives = r.positives.saturating_add(1);
            if t.fired {
                r.detected = r.detected.saturating_add(1);
                if let Some(ms) = t.reaction_ms {
                    reactions.push(ms);
                }
            }
            continue;
        }
        r.negatives = r.negatives.saturating_add(1);
        if t.background.is_noisy() {
            r.background_negatives = r.background_negatives.saturating_add(1);
        }
        if t.fired {
            r.false_barges = r.false_barges.saturating_add(1);
            if t.background.is_noisy() {
                r.background_false_barges = r.background_false_barges.saturating_add(1);
            }
        }
    }
    r.miss_rate = ratio(r.positives.saturating_sub(r.detected), r.positives);
    r.false_rate = ratio(r.false_barges, r.negatives);
    r.background_false_rate = ratio(r.background_false_barges, r.background_negatives);
    r.reaction = summarize(&reactions)?;
    Ok(r)
}
