use serde::{Deserialize, Serialize};

use crate::error::{EngineError, EngineResult};

pub const DAY_MS: u64 = 86_400_000;
pub const MAX_CONFIG_BYTES: usize = 8 * 1024;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Gate {
    pub min_days: u16,
    pub min_samples: u32,
    pub min_agreement_bps: u16,
    pub max_invalid_bps: u16,
    pub max_wrong_action: u32,
}

impl Default for Gate {
    fn default() -> Self {
        Self {
            min_days: 7,
            min_samples: 200,
            min_agreement_bps: 9_500,
            max_invalid_bps: 500,
            max_wrong_action: 0,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Config {
    pub retrieve_limit: u8,
    pub max_corrections: u8,
    pub cache_capacity: u32,
    pub cache_ttl_ms: u64,
    pub understand_threshold_bps: u16,
    pub gate: Gate,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            retrieve_limit: 8,
            max_corrections: 1,
            cache_capacity: 512,
            cache_ttl_ms: DAY_MS,
            understand_threshold_bps: reason_understand::DEFAULT_THRESHOLD_BPS,
            gate: Gate::default(),
        }
    }
}

impl Config {
    pub fn parse(raw: &str) -> EngineResult<Self> {
        if raw.len() > MAX_CONFIG_BYTES {
            return Err(EngineError::Config("too_large"));
        }
        let config: Self = serde_json::from_str(raw).map_err(|_| EngineError::Config("schema"))?;
        config.validate()?;
        Ok(config)
    }

    pub fn validate(&self) -> EngineResult<()> {
        let bps = |v: u16| v <= 10_000;
        if !(1..=24).contains(&self.retrieve_limit) {
            return Err(EngineError::Config("retrieve_limit"));
        }
        if self.max_corrections > 3 {
            return Err(EngineError::Config("max_corrections"));
        }
        if !(1..=100_000).contains(&self.cache_capacity) {
            return Err(EngineError::Config("cache_capacity"));
        }
        if !(1_000..=30 * DAY_MS).contains(&self.cache_ttl_ms) {
            return Err(EngineError::Config("cache_ttl_ms"));
        }
        if !bps(self.understand_threshold_bps) {
            return Err(EngineError::Config("understand_threshold_bps"));
        }
        let gate = &self.gate;
        if !(1..=30).contains(&gate.min_days) || gate.min_samples == 0 {
            return Err(EngineError::Config("gate_window"));
        }
        if !bps(gate.min_agreement_bps) || !bps(gate.max_invalid_bps) {
            return Err(EngineError::Config("gate_bps"));
        }
        Ok(())
    }
}
