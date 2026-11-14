use serde::{Deserialize, Serialize};

use crate::error::{BenchError, BenchResult};
use crate::observations::SCHEMA;

pub const SECTIONS: [&str; 5] = ["latency", "wer", "wake", "speaker", "barge"];

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Limit {
    pub warn: f64,
    pub fail: f64,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Tolerance {
    pub latency_ratio: f64,
    pub rate_abs: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Thresholds {
    pub schema: u32,
    pub required: Vec<String>,
    pub min_utterances: u64,
    pub min_wake_positives: u64,
    pub min_wake_negative_hours: f64,
    pub min_speaker_trials: u64,
    pub min_barge_trials: u64,
    pub e2e_p50_ms: Limit,
    pub e2e_p95_ms: Limit,
    pub e2e_p99_ms: Limit,
    pub wer: Limit,
    pub wake_miss_rate: Limit,
    pub wake_false_accepts_per_hour: Limit,
    pub wake_background_false_accepts_per_hour: Limit,
    pub known_miss_rate: Limit,
    pub false_known_rate: Limit,
    pub guest_as_known_rate: Limit,
    pub broadcast_as_known_rate: Limit,
    pub background_false_known_rate: Limit,
    pub barge_miss_rate: Limit,
    pub barge_false_rate: Limit,
    pub barge_background_false_rate: Limit,
    pub barge_reaction_p95_ms: Limit,
    pub tolerance: Tolerance,
}

const fn limit(warn: f64, fail: f64) -> Limit {
    Limit { warn, fail }
}

impl Default for Thresholds {
    fn default() -> Self {
        Self {
            schema: SCHEMA,
            required: SECTIONS.iter().map(|s| (*s).to_owned()).collect(),
            min_utterances: 30,
            min_wake_positives: 20,
            min_wake_negative_hours: 1.0,
            min_speaker_trials: 50,
            min_barge_trials: 30,
            e2e_p50_ms: limit(900.0, 1_500.0),
            e2e_p95_ms: limit(1_800.0, 3_000.0),
            e2e_p99_ms: limit(3_000.0, 5_000.0),
            wer: limit(0.08, 0.15),
            wake_miss_rate: limit(0.05, 0.15),
            wake_false_accepts_per_hour: limit(0.5, 2.0),
            wake_background_false_accepts_per_hour: limit(1.0, 3.0),
            known_miss_rate: limit(0.05, 0.15),
            false_known_rate: limit(0.02, 0.05),
            guest_as_known_rate: limit(0.01, 0.03),
            broadcast_as_known_rate: limit(0.01, 0.03),
            background_false_known_rate: limit(0.01, 0.03),
            barge_miss_rate: limit(0.10, 0.25),
            barge_false_rate: limit(0.02, 0.05),
            barge_background_false_rate: limit(0.03, 0.08),
            barge_reaction_p95_ms: limit(400.0, 800.0),
            tolerance: Tolerance {
                latency_ratio: 0.10,
                rate_abs: 0.01,
            },
        }
    }
}

impl Thresholds {
    #[must_use]
    pub fn rules(&self) -> [(&'static str, Limit); 16] {
        [
            ("e2e_p50_ms", self.e2e_p50_ms),
            ("e2e_p95_ms", self.e2e_p95_ms),
            ("e2e_p99_ms", self.e2e_p99_ms),
            ("wer", self.wer),
            ("wake_miss_rate", self.wake_miss_rate),
            (
                "wake_false_accepts_per_hour",
                self.wake_false_accepts_per_hour,
            ),
            (
                "wake_background_false_accepts_per_hour",
                self.wake_background_false_accepts_per_hour,
            ),
            ("known_miss_rate", self.known_miss_rate),
            ("false_known_rate", self.false_known_rate),
            ("guest_as_known_rate", self.guest_as_known_rate),
            ("broadcast_as_known_rate", self.broadcast_as_known_rate),
            (
                "background_false_known_rate",
                self.background_false_known_rate,
            ),
            ("barge_miss_rate", self.barge_miss_rate),
            ("barge_false_rate", self.barge_false_rate),
            (
                "barge_background_false_rate",
                self.barge_background_false_rate,
            ),
            ("barge_reaction_p95_ms", self.barge_reaction_p95_ms),
        ]
    }

    pub fn validate(&self) -> BenchResult<()> {
        if self.schema != SCHEMA {
            return Err(BenchError::Invalid("thresholds_schema"));
        }
        for (_, l) in self.rules() {
            let finite = l.warn.is_finite() && l.fail.is_finite();
            if !finite || l.warn < 0.0 || l.warn > l.fail {
                return Err(BenchError::Invalid("thresholds_limit"));
            }
        }
        let t = self.tolerance;
        if !t.latency_ratio.is_finite()
            || !t.rate_abs.is_finite()
            || t.latency_ratio < 0.0
            || t.rate_abs < 0.0
            || !self.min_wake_negative_hours.is_finite()
            || self.min_wake_negative_hours < 0.0
        {
            return Err(BenchError::Invalid("thresholds_tolerance"));
        }
        if self
            .required
            .iter()
            .any(|s| !SECTIONS.contains(&s.as_str()))
        {
            return Err(BenchError::Invalid("thresholds_required"));
        }
        Ok(())
    }

    pub fn parse(bytes: &[u8]) -> BenchResult<Self> {
        let t: Self = serde_json::from_slice(bytes)?;
        t.validate()?;
        Ok(t)
    }
}
