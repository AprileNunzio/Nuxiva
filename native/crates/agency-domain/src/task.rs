use std::collections::BTreeSet;

use serde::{Deserialize, Serialize};

use crate::budget::Usage;
use crate::error::DomainError;
use crate::ids::{RoleId, TaskId};
use crate::text::CleanText;

const MAX_TITLE: usize = 300;
const MAX_CRITERION: usize = 500;
const MAX_FEEDBACK: usize = 4_000;
const MAX_CRITERIA: usize = 16;
const MAX_DEPENDENCIES: usize = 64;
const MAX_ATTEMPTS: u8 = 10;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TaskStatus {
    Pending,
    Running,
    Review,
    Done,
    Failed,
    Cancelled,
}

impl TaskStatus {
    #[must_use]
    pub fn name(self) -> &'static str {
        match self {
            Self::Pending => "pending",
            Self::Running => "running",
            Self::Review => "review",
            Self::Done => "done",
            Self::Failed => "failed",
            Self::Cancelled => "cancelled",
        }
    }

    #[must_use]
    pub fn is_terminal(self) -> bool {
        matches!(self, Self::Done | Self::Failed | Self::Cancelled)
    }

    #[must_use]
    pub fn can_become(self, next: Self) -> bool {
        use TaskStatus::{Cancelled, Done, Failed, Pending, Review, Running};
        matches!(
            (self, next),
            (Pending, Running | Cancelled)
                | (Running, Review | Failed | Cancelled | Pending)
                | (Review, Done | Pending | Failed | Cancelled)
        )
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Criterion {
    text: CleanText,
    verified: bool,
}

impl Criterion {
    #[must_use]
    pub fn text(&self) -> &CleanText {
        &self.text
    }

    #[must_use]
    pub fn verified(&self) -> bool {
        self.verified
    }
}

#[derive(Debug, Clone, Default, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TaskSpec {
    pub id: String,
    pub title: String,
    pub role: String,
    #[serde(default)]
    pub depends_on: Vec<String>,
    #[serde(default)]
    pub acceptance: Vec<String>,
    #[serde(default)]
    pub estimate_seconds: u64,
    #[serde(default)]
    pub max_attempts: u8,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Task {
    id: TaskId,
    title: CleanText,
    role: RoleId,
    depends_on: BTreeSet<TaskId>,
    acceptance: Vec<Criterion>,
    status: TaskStatus,
    attempts: u8,
    max_attempts: u8,
    estimate_seconds: u64,
    feedback: Option<CleanText>,
    usage: Usage,
}

impl Task {
    pub fn from_spec(spec: &TaskSpec) -> Result<Self, DomainError> {
        let id = TaskId::new(&spec.id)?;
        if spec.depends_on.len() > MAX_DEPENDENCIES {
            return Err(DomainError::InvalidText {
                field: "depends_on",
                reason: "too many dependencies",
            });
        }
        if spec.acceptance.len() > MAX_CRITERIA {
            return Err(DomainError::InvalidText {
                field: "acceptance",
                reason: "too many criteria",
            });
        }
        let depends_on = spec
            .depends_on
            .iter()
            .map(|raw| TaskId::new(raw))
            .collect::<Result<BTreeSet<_>, _>>()?;
        if depends_on.contains(&id) {
            return Err(DomainError::InvalidId(format!("{id} depends on itself")));
        }
        let acceptance = spec
            .acceptance
            .iter()
            .map(|raw| {
                CleanText::new("acceptance", raw, MAX_CRITERION).map(|text| Criterion {
                    text,
                    verified: false,
                })
            })
            .collect::<Result<Vec<_>, _>>()?;
        let max_attempts = match spec.max_attempts {
            0 => 3,
            n => n.min(MAX_ATTEMPTS),
        };
        Ok(Self {
            id,
            title: CleanText::new("title", &spec.title, MAX_TITLE)?,
            role: RoleId::new(&spec.role)?,
            depends_on,
            acceptance,
            status: TaskStatus::Pending,
            attempts: 0,
            max_attempts,
            estimate_seconds: spec.estimate_seconds,
            feedback: None,
            usage: Usage::default(),
        })
    }

    #[must_use]
    pub fn id(&self) -> &TaskId {
        &self.id
    }

    #[must_use]
    pub fn title(&self) -> &CleanText {
        &self.title
    }

    #[must_use]
    pub fn role(&self) -> &RoleId {
        &self.role
    }

    #[must_use]
    pub fn depends_on(&self) -> &BTreeSet<TaskId> {
        &self.depends_on
    }

    #[must_use]
    pub fn acceptance(&self) -> &[Criterion] {
        &self.acceptance
    }

    #[must_use]
    pub fn status(&self) -> TaskStatus {
        self.status
    }

    #[must_use]
    pub fn attempts(&self) -> u8 {
        self.attempts
    }

    #[must_use]
    pub fn max_attempts(&self) -> u8 {
        self.max_attempts
    }

    #[must_use]
    pub fn estimate_seconds(&self) -> u64 {
        self.estimate_seconds
    }

    #[must_use]
    pub fn feedback(&self) -> Option<&CleanText> {
        self.feedback.as_ref()
    }

    #[must_use]
    pub fn usage(&self) -> &Usage {
        &self.usage
    }

    pub fn record_usage(&mut self, tokens: u64, seconds: u64) -> Result<(), DomainError> {
        self.usage.record(tokens, seconds)
    }

    fn move_to(&mut self, next: TaskStatus) -> Result<(), DomainError> {
        if !self.status.can_become(next) {
            return Err(DomainError::Transition {
                from: self.status.name(),
                to: next.name(),
            });
        }
        self.status = next;
        Ok(())
    }

    pub fn start(&mut self) -> Result<(), DomainError> {
        if self.attempts >= self.max_attempts {
            return Err(DomainError::AttemptsExhausted);
        }
        self.move_to(TaskStatus::Running)?;
        self.attempts = self.attempts.saturating_add(1);
        Ok(())
    }

    pub fn interrupt(&mut self) -> Result<(), DomainError> {
        self.move_to(TaskStatus::Pending)?;
        self.attempts = self.attempts.saturating_sub(1);
        Ok(())
    }

    pub fn submit(&mut self) -> Result<(), DomainError> {
        self.move_to(TaskStatus::Review)
    }

    pub fn approve(&mut self) -> Result<(), DomainError> {
        self.move_to(TaskStatus::Done)?;
        self.feedback = None;
        for criterion in &mut self.acceptance {
            criterion.verified = true;
        }
        Ok(())
    }

    pub fn rework(&mut self, feedback: &str) -> Result<(), DomainError> {
        let note = CleanText::new("feedback", feedback, MAX_FEEDBACK)?;
        if self.attempts >= self.max_attempts {
            self.move_to(TaskStatus::Failed)?;
            self.feedback = Some(note);
            return Err(DomainError::AttemptsExhausted);
        }
        self.move_to(TaskStatus::Pending)?;
        self.feedback = Some(note);
        Ok(())
    }

    pub fn fail(&mut self) -> Result<(), DomainError> {
        self.move_to(TaskStatus::Failed)
    }

    pub fn cancel(&mut self) -> Result<(), DomainError> {
        self.move_to(TaskStatus::Cancelled)
    }
}
