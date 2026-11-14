use serde::{Deserialize, Serialize};

use crate::error::{TaskqError, TaskqResult};
use crate::limits::Ceilings;

pub const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Class {
    Voice,
    Interactive,
    Background,
    Maintenance,
}

impl Class {
    pub const ALL: [Self; 4] = [
        Self::Voice,
        Self::Interactive,
        Self::Background,
        Self::Maintenance,
    ];

    #[must_use]
    pub const fn index(self) -> usize {
        match self {
            Self::Voice => 0,
            Self::Interactive => 1,
            Self::Background => 2,
            Self::Maintenance => 3,
        }
    }

    #[must_use]
    pub const fn name(self) -> &'static str {
        match self {
            Self::Voice => "voice",
            Self::Interactive => "interactive",
            Self::Background => "background",
            Self::Maintenance => "maintenance",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Risk {
    None,
    Low,
    Medium,
    High,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Budget {
    pub wall_ms: u64,
    pub tokens: u64,
    pub tool_calls: u64,
    pub cpu_ms: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TaskSpec {
    pub schema_version: u32,
    pub id: String,
    #[serde(default)]
    pub parent: Option<String>,
    pub kind: String,
    pub class: Class,
    pub priority: u8,
    #[serde(default)]
    pub deps: Vec<String>,
    #[serde(default)]
    pub scope: Vec<String>,
    pub budget: Budget,
    pub risk_max: Risk,
    pub input_ref: String,
    #[serde(default)]
    pub idem_key: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TaskState {
    Queued,
    Running,
    Retrying,
    Done,
    Failed,
    Cancelled,
    Expired,
}

impl TaskState {
    #[must_use]
    pub const fn is_terminal(self) -> bool {
        matches!(
            self,
            Self::Done | Self::Failed | Self::Cancelled | Self::Expired
        )
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ErrorPayload {
    pub code: String,
    pub transient: bool,
}

impl ErrorPayload {
    #[must_use]
    pub fn new(code: &str, transient: bool) -> Self {
        Self {
            code: code.chars().take(Ceilings::IDENT).collect(),
            transient,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TaskEvent {
    pub id: String,
    pub state: TaskState,
    pub class: Class,
    pub attempt: u32,
    pub progress: u8,
    pub evidence: Vec<String>,
    pub error: Option<ErrorPayload>,
}

#[must_use]
pub fn valid_ident(text: &str) -> bool {
    !text.is_empty()
        && text.len() <= Ceilings::IDENT
        && text.bytes().all(|b| {
            b.is_ascii_lowercase() || b.is_ascii_digit() || matches!(b, b'.' | b'_' | b':' | b'-')
        })
}

impl TaskSpec {
    pub fn validate(&self) -> TaskqResult<()> {
        if self.schema_version != SCHEMA_VERSION {
            return Err(TaskqError::Version);
        }
        let idents_ok = valid_ident(&self.id)
            && self.parent.as_deref().is_none_or(valid_ident)
            && self.idem_key.as_deref().is_none_or(valid_ident)
            && self.deps.iter().all(|d| valid_ident(d) && d != &self.id)
            && self.scope.iter().all(|s| valid_ident(s));
        let sizes_ok = !self.kind.is_empty()
            && self.kind.len() <= Ceilings::KIND
            && self.kind.bytes().all(|b| {
                b.is_ascii_lowercase() || b.is_ascii_digit() || matches!(b, b'.' | b'_' | b'-')
            })
            && self.deps.len() <= Ceilings::DEPS
            && self.scope.len() <= Ceilings::SCOPE
            && self.input_ref.len() <= Ceilings::INPUT_REF
            && !self.input_ref.chars().any(char::is_control);
        let budget_ok = (1..=Ceilings::TIME_MS).contains(&self.budget.wall_ms)
            && self.budget.tokens <= Ceilings::TOKENS
            && self.budget.tool_calls <= Ceilings::TOKENS
            && self.budget.cpu_ms <= Ceilings::TIME_MS;
        let parent_ok = self.parent.as_deref() != Some(self.id.as_str());
        if idents_ok && sizes_ok && budget_ok && parent_ok {
            Ok(())
        } else {
            Err(TaskqError::Invalid)
        }
    }

    pub fn from_json(text: &str) -> TaskqResult<Self> {
        if text.len() > Ceilings::PAYLOAD_BYTES {
            return Err(TaskqError::TooLarge);
        }
        let spec: Self = serde_json::from_str(text).map_err(|_| TaskqError::Parse)?;
        spec.validate()?;
        Ok(spec)
    }

    pub fn to_json(&self) -> TaskqResult<String> {
        serde_json::to_string(self).map_err(|_| TaskqError::Serialize)
    }
}
