use serde::{Deserialize, Serialize};

use super::ident::{Digest, Ident};
use super::{Validate, version};
use crate::error::{SwarmError, SwarmResult};
use crate::settings::Settings;

pub const MAX_RISK: u8 = 4;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Level {
    Lampo,
    Standard,
    Progetto,
}

impl From<nuxiva_agent_core::ceo::Level> for Level {
    fn from(value: nuxiva_agent_core::ceo::Level) -> Self {
        match value {
            nuxiva_agent_core::ceo::Level::Lampo => Self::Lampo,
            nuxiva_agent_core::ceo::Level::Standard => Self::Standard,
            nuxiva_agent_core::ceo::Level::Progetto => Self::Progetto,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Constraints {
    pub risk_max: u8,
    pub deadline_ms: u64,
    pub tokens_max: u64,
    pub tool_calls_max: u64,
    pub level: Level,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TaskEnvelope {
    pub schema_version: u32,
    pub id: Ident,
    pub intent: Ident,
    pub input: Ident,
    pub constraints: Constraints,
    #[serde(default)]
    pub parent: Option<Ident>,
    #[serde(default)]
    pub context_ref: Option<Ident>,
    #[serde(default)]
    pub graph_ref: Option<Digest>,
    #[serde(default)]
    pub depth: u8,
}

impl Validate for Constraints {
    fn validate(&self, settings: &Settings) -> SwarmResult<()> {
        let ok = self.risk_max <= MAX_RISK
            && (1..=settings.max_time_ms).contains(&self.deadline_ms)
            && (1..=settings.max_tokens).contains(&self.tokens_max)
            && (1..=settings.max_tool_calls).contains(&self.tool_calls_max);
        if ok { Ok(()) } else { Err(SwarmError::Budget) }
    }
}

impl Validate for TaskEnvelope {
    fn validate(&self, settings: &Settings) -> SwarmResult<()> {
        version(self.schema_version)?;
        self.constraints.validate(settings)?;
        if usize::from(self.depth) > settings.max_redelegation_depth {
            return Err(SwarmError::Budget);
        }
        Ok(())
    }
}
