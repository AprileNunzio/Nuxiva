use serde::{Deserialize, Serialize};
use serde_json::Value;

use super::ident::Ident;
use super::{Validate, version};
use crate::error::{SwarmError, SwarmResult};
use crate::settings::Settings;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Outcome {
    Done,
    Failed,
    Cancelled,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Usage {
    pub tokens: u64,
    pub tool_calls: u64,
    pub time_ms: u64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct WorkerResult {
    pub schema_version: u32,
    pub task: Ident,
    pub step: Ident,
    pub outcome: Outcome,
    pub output: Value,
    #[serde(default)]
    pub evidence: Vec<Ident>,
    #[serde(default)]
    pub usage: Usage,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum WorkerErrorKind {
    GraphNotConsulted,
    BudgetExceeded,
    Timeout,
    Denied,
    ConsentRequired,
    Invalid,
    Unavailable,
    Cancelled,
    Internal,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct WorkerError {
    pub schema_version: u32,
    pub kind: WorkerErrorKind,
    pub code: Ident,
    pub step: Ident,
    pub retryable: bool,
}

impl Validate for WorkerResult {
    fn validate(&self, settings: &Settings) -> SwarmResult<()> {
        version(self.schema_version)?;
        if self.evidence.len() > settings.max_evidence {
            return Err(SwarmError::TooLarge);
        }
        let size = serde_json::to_vec(&self.output).map_err(|_| SwarmError::Serialize)?;
        if size.len() > settings.max_output_bytes {
            return Err(SwarmError::TooLarge);
        }
        Ok(())
    }
}

impl Validate for WorkerError {
    fn validate(&self, _settings: &Settings) -> SwarmResult<()> {
        version(self.schema_version)
    }
}

impl WorkerError {
    #[must_use]
    pub fn new(kind: WorkerErrorKind, code: Ident, step: Ident) -> Self {
        let retryable = matches!(
            kind,
            WorkerErrorKind::GraphNotConsulted
                | WorkerErrorKind::Timeout
                | WorkerErrorKind::Unavailable
        );
        Self {
            schema_version: super::SCHEMA_VERSION,
            kind,
            code,
            step,
            retryable,
        }
    }
}
