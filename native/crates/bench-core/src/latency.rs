use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::error::{BenchError, BenchResult};
use crate::stats::{Summary, summarize};

pub const MAX_STAGE_MS: f64 = 600_000.0;
pub const STAGES: [&str; 5] = ["listen", "transcribe", "decide", "respond", "tts"];

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct StageTimes {
    pub listen_ms: f64,
    pub transcribe_ms: f64,
    pub decide_ms: f64,
    pub respond_ms: f64,
    pub tts_ms: f64,
}

impl StageTimes {
    #[must_use]
    pub fn parts(&self) -> [f64; 5] {
        [
            self.listen_ms,
            self.transcribe_ms,
            self.decide_ms,
            self.respond_ms,
            self.tts_ms,
        ]
    }

    #[must_use]
    pub fn total(&self) -> f64 {
        self.parts().iter().sum()
    }

    pub fn validate(&self) -> BenchResult<()> {
        if self
            .parts()
            .iter()
            .any(|v| !v.is_finite() || *v < 0.0 || *v > MAX_STAGE_MS)
        {
            return Err(BenchError::Invalid("stage_ms"));
        }
        Ok(())
    }
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct LatencyReport {
    pub end_to_end: Summary,
    pub stages: BTreeMap<String, Summary>,
}

pub fn analyze(times: &[StageTimes]) -> BenchResult<LatencyReport> {
    for t in times {
        t.validate()?;
    }
    let totals: Vec<f64> = times.iter().map(StageTimes::total).collect();
    let mut stages = BTreeMap::new();
    for (index, name) in STAGES.iter().enumerate() {
        let column: Vec<f64> = times
            .iter()
            .map(|t| t.parts().get(index).copied().unwrap_or_default())
            .collect();
        stages.insert((*name).to_owned(), summarize(&column)?);
    }
    Ok(LatencyReport {
        end_to_end: summarize(&totals)?,
        stages,
    })
}
