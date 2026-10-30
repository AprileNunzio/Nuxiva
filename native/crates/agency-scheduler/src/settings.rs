use serde::{Deserialize, Serialize};
use thiserror::Error;

pub const HARD_CAP: u16 = 64;
const MAX_RESERVE_MB: u64 = 1 << 20;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Mode {
    Auto,
    Manual,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Error)]
pub enum SettingsError {
    #[error("parallel agents must be between 1 and {HARD_CAP}")]
    Parallel,
    #[error("reserved memory is out of range")]
    Reserve,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Settings {
    pub mode: Mode,
    pub manual_parallel: u16,
    pub max_parallel: u16,
    pub reserve_ram_mb: u64,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            mode: Mode::Auto,
            manual_parallel: 2,
            max_parallel: 16,
            reserve_ram_mb: 2_048,
        }
    }
}

impl Settings {
    pub fn validate(self) -> Result<Self, SettingsError> {
        let in_range = |n: u16| (1..=HARD_CAP).contains(&n);
        if !in_range(self.manual_parallel) || !in_range(self.max_parallel) {
            return Err(SettingsError::Parallel);
        }
        if self.reserve_ram_mb > MAX_RESERVE_MB {
            return Err(SettingsError::Reserve);
        }
        Ok(self)
    }
}
