use serde::{Deserialize, Serialize};

use crate::barge::BargeTrial;
use crate::error::{BenchError, BenchResult};
use crate::latency::StageTimes;
use crate::speaker::SpeakerTrial;
use crate::wake::WakeTrial;

pub const SCHEMA: u32 = 1;
pub const MAX_ITEMS: usize = 200_000;
pub const MAX_TEXT_CHARS: usize = 4_096;
pub const MAX_TOKEN: usize = 64;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Source {
    Synthetic,
    Recorded,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct UtteranceObs {
    pub id: String,
    pub reference: String,
    pub hypothesis: String,
    pub stages: StageTimes,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Observations {
    pub schema: u32,
    pub source: Source,
    pub corpus: String,
    #[serde(default)]
    pub utterances: Vec<UtteranceObs>,
    #[serde(default)]
    pub wake: Vec<WakeTrial>,
    #[serde(default)]
    pub speaker: Vec<SpeakerTrial>,
    #[serde(default)]
    pub barge: Vec<BargeTrial>,
}

#[must_use]
pub fn is_token(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= MAX_TOKEN
        && value
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'_' || b == b'.')
}

fn clean_text(value: &str) -> bool {
    value.chars().count() <= MAX_TEXT_CHARS && !value.chars().any(char::is_control)
}

impl Observations {
    pub fn validate(&self) -> BenchResult<()> {
        if self.schema != SCHEMA {
            return Err(BenchError::Invalid("schema"));
        }
        if !is_token(&self.corpus) {
            return Err(BenchError::Invalid("corpus"));
        }
        if self.utterances.len() > MAX_ITEMS
            || self.wake.len() > MAX_ITEMS
            || self.speaker.len() > MAX_ITEMS
            || self.barge.len() > MAX_ITEMS
        {
            return Err(BenchError::TooLarge("observations"));
        }
        for u in &self.utterances {
            if !is_token(&u.id) {
                return Err(BenchError::Invalid("utterance_id"));
            }
            if !clean_text(&u.reference) || !clean_text(&u.hypothesis) {
                return Err(BenchError::Invalid("utterance_text"));
            }
            u.stages.validate()?;
        }
        for w in &self.wake {
            w.validate()?;
        }
        for b in &self.barge {
            b.validate()?;
        }
        Ok(())
    }

    pub fn fingerprint(&self) -> BenchResult<String> {
        let bytes = serde_json::to_vec(self)?;
        Ok(blake3::hash(&bytes).to_hex().to_string())
    }

    pub fn parse(bytes: &[u8]) -> BenchResult<Self> {
        let obs: Self = serde_json::from_slice(bytes)?;
        obs.validate()?;
        Ok(obs)
    }
}
