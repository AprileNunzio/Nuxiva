use serde::{Deserialize, Serialize};

use crate::catalog::{Catalog, name_ok};
use crate::error::{ReflectError, ReflectResult};
use crate::settings::{MAX_PAYLOAD, Settings};

pub const SCHEMA_VERSION: u32 = 1;
pub const MAX_OBSERVED: usize = 16;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Outcome {
    Success,
    Failure,
    Cancelled,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Signals {
    pub duration_ms: u64,
    pub attempts: u32,
    pub user_corrections: u32,
    pub user_rejections: u32,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Observed {
    pub kind: String,
    pub value: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Candidate {
    pub kind: String,
    pub value: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case", tag = "type")]
pub enum Delta {
    Data { candidate: Candidate },
    Code { request_ref: String },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Reflection {
    pub schema_version: u32,
    pub task: String,
    pub outcome: Outcome,
    pub signals: Signals,
    #[serde(default)]
    pub observed: Vec<Observed>,
    #[serde(default)]
    pub proposed: Option<Delta>,
}

impl Reflection {
    pub fn validate(&self, catalog: &Catalog) -> ReflectResult<()> {
        if self.schema_version != SCHEMA_VERSION {
            return Err(ReflectError::Version);
        }
        let ok = name_ok(&self.task)
            && self.observed.len() <= MAX_OBSERVED
            && self.signals.attempts <= 1_000
            && self.signals.user_corrections <= 1_000
            && self.signals.user_rejections <= 1_000;
        if !ok {
            return Err(ReflectError::Invalid);
        }
        for o in &self.observed {
            catalog.check(&o.kind, &o.value)?;
        }
        match &self.proposed {
            Some(Delta::Data { candidate }) => {
                catalog.check(&candidate.kind, &candidate.value)?;
            }
            Some(Delta::Code { request_ref })
                if request_ref.is_empty()
                    || request_ref.len() > 512
                    || request_ref.chars().any(char::is_control) =>
            {
                return Err(ReflectError::Invalid);
            }
            _ => {}
        }
        Ok(())
    }

    #[must_use]
    pub fn score(&self, settings: &Settings) -> u32 {
        let base: u32 = match self.outcome {
            Outcome::Success => 1_000,
            Outcome::Failure => 0,
            Outcome::Cancelled => settings.cancelled_score,
        };
        let penalty = self
            .signals
            .attempts
            .saturating_sub(1)
            .saturating_mul(settings.attempt_penalty)
            .saturating_add(
                self.signals
                    .user_corrections
                    .saturating_mul(settings.correction_penalty),
            )
            .saturating_add(
                self.signals
                    .user_rejections
                    .saturating_mul(settings.rejection_penalty),
            );
        base.saturating_sub(penalty)
    }

    pub fn from_json(text: &str) -> ReflectResult<Self> {
        if text.len() > MAX_PAYLOAD {
            return Err(ReflectError::TooLarge);
        }
        serde_json::from_str(text).map_err(|_| ReflectError::Parse)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum LessonState {
    Candidate,
    Adopted,
    Rejected,
    Expired,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Lesson {
    pub id: u64,
    pub kind: String,
    pub domain: String,
    pub value: String,
    pub state: LessonState,
    pub version: u32,
    pub evidence: u32,
    pub user_confirmed: bool,
    pub created_at: u64,
    pub confirmed_at: u64,
}
