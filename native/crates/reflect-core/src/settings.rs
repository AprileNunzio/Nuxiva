use serde::{Deserialize, Serialize};

use crate::error::{ReflectError, ReflectResult};

pub const MAX_PAYLOAD: usize = 2 * 1024 * 1024;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Settings {
    pub history_cap: usize,
    pub min_samples: usize,
    pub margin_permille: u32,
    pub ttl_ms: u64,
    pub block_ms: u64,
    pub domain_cap: usize,
    pub attempt_penalty: u32,
    pub correction_penalty: u32,
    pub rejection_penalty: u32,
    pub cancelled_score: u32,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            history_cap: 2_048,
            min_samples: 5,
            margin_permille: 50,
            ttl_ms: 14 * 86_400_000,
            block_ms: 30 * 86_400_000,
            domain_cap: 32,
            attempt_penalty: 100,
            correction_penalty: 150,
            rejection_penalty: 300,
            cancelled_score: 300,
        }
    }
}

impl Settings {
    pub fn validate(&self) -> ReflectResult<()> {
        let ok = (1..=65_536).contains(&self.history_cap)
            && (1..=self.history_cap).contains(&self.min_samples)
            && self.margin_permille <= 1_000
            && (1..=365 * 86_400_000).contains(&self.ttl_ms)
            && (1..=365 * 86_400_000).contains(&self.block_ms)
            && (1..=1_024).contains(&self.domain_cap)
            && self.attempt_penalty <= 1_000
            && self.correction_penalty <= 1_000
            && self.rejection_penalty <= 1_000
            && self.cancelled_score <= 1_000;
        if ok {
            Ok(())
        } else {
            Err(ReflectError::Settings)
        }
    }

    pub fn from_json(text: &str) -> ReflectResult<Self> {
        if text.len() > MAX_PAYLOAD {
            return Err(ReflectError::TooLarge);
        }
        let settings: Self = serde_json::from_str(text).map_err(|_| ReflectError::Settings)?;
        settings.validate()?;
        Ok(settings)
    }
}
