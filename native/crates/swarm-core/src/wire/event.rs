use serde::{Deserialize, Serialize};

use super::ident::Ident;
use super::{Validate, version};
use crate::error::SwarmResult;
use crate::settings::Settings;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Phase {
    Queued,
    Started,
    Done,
    Failed,
    Cancelled,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct StepEvent {
    pub schema_version: u32,
    pub task: Ident,
    pub step: Ident,
    pub phase: Phase,
    pub at_ms: u64,
}

impl Validate for StepEvent {
    fn validate(&self, _settings: &Settings) -> SwarmResult<()> {
        version(self.schema_version)
    }
}
