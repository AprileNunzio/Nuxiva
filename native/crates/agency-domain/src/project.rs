use std::path::{Path, PathBuf};

use serde::{Deserialize, Deserializer, Serialize, Serializer};

use crate::budget::{Budget, Usage};
use crate::error::DomainError;
use crate::ids::ProjectId;
use crate::text::CleanText;

const MAX_TITLE: usize = 200;
const MAX_GOAL: usize = 8_000;
const MAX_DEPTH: usize = 8;
const MAX_SEGMENT: usize = 64;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ProjectStatus {
    Planning,
    Running,
    WaitingUser,
    Paused,
    Completed,
    Failed,
    Cancelled,
}

impl ProjectStatus {
    #[must_use]
    pub fn name(self) -> &'static str {
        match self {
            Self::Planning => "planning",
            Self::Running => "running",
            Self::WaitingUser => "waiting_user",
            Self::Paused => "paused",
            Self::Completed => "completed",
            Self::Failed => "failed",
            Self::Cancelled => "cancelled",
        }
    }

    #[must_use]
    pub fn is_terminal(self) -> bool {
        matches!(self, Self::Completed | Self::Failed | Self::Cancelled)
    }

    #[must_use]
    pub fn can_become(self, next: Self) -> bool {
        use ProjectStatus::{Cancelled, Completed, Failed, Paused, Planning, Running, WaitingUser};
        if self.is_terminal() || self == next {
            return false;
        }
        match next {
            Cancelled | Failed => true,
            Running => matches!(self, Planning | Paused | WaitingUser),
            Planning => matches!(self, Running | Paused | WaitingUser),
            Paused => matches!(self, Planning | Running | WaitingUser),
            WaitingUser => matches!(self, Planning | Running),
            Completed => self == Running,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WorkspacePath(PathBuf);

impl WorkspacePath {
    pub fn new(raw: &str) -> Result<Self, DomainError> {
        if raw.is_empty() {
            return Err(DomainError::InvalidWorkspace("empty path"));
        }
        let segments: Vec<&str> = raw.split('/').collect();
        if segments.len() > MAX_DEPTH {
            return Err(DomainError::InvalidWorkspace("path too deep"));
        }
        let mut clean = PathBuf::new();
        for segment in segments {
            validate_segment(segment)?;
            clean.push(segment);
        }
        Ok(Self(clean))
    }

    #[must_use]
    pub fn as_path(&self) -> &Path {
        &self.0
    }

    #[must_use]
    pub fn resolve(&self, root: &Path) -> PathBuf {
        root.join(&self.0)
    }
}

fn validate_segment(text: &str) -> Result<(), DomainError> {
    let allowed = |c: char| c.is_alphanumeric() || matches!(c, '-' | '_' | '.' | ' ');
    if text.is_empty() || text.chars().count() > MAX_SEGMENT {
        return Err(DomainError::InvalidWorkspace("segment length"));
    }
    if text.starts_with('.') || text.ends_with(' ') || text.ends_with('.') {
        return Err(DomainError::InvalidWorkspace("hidden or trailing segment"));
    }
    if !text.chars().all(allowed) {
        return Err(DomainError::InvalidWorkspace("forbidden character"));
    }
    Ok(())
}

impl Serialize for WorkspacePath {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        serializer.serialize_str(&self.0.to_string_lossy())
    }
}

impl<'de> Deserialize<'de> for WorkspacePath {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        let raw = String::deserialize(deserializer)?;
        Self::new(&raw).map_err(serde::de::Error::custom)
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Project {
    id: ProjectId,
    title: CleanText,
    goal: CleanText,
    status: ProjectStatus,
    workspace: WorkspacePath,
    budget: Budget,
    usage: Usage,
    created_at_ms: u64,
}

impl Project {
    pub fn new(
        id: ProjectId,
        title: &str,
        goal: &str,
        workspace: WorkspacePath,
        budget: Budget,
        created_at_ms: u64,
    ) -> Result<Self, DomainError> {
        Ok(Self {
            id,
            title: CleanText::new("title", title, MAX_TITLE)?,
            goal: CleanText::new("goal", goal, MAX_GOAL)?,
            status: ProjectStatus::Planning,
            workspace,
            budget,
            usage: Usage::default(),
            created_at_ms,
        })
    }

    #[must_use]
    pub fn id(&self) -> &ProjectId {
        &self.id
    }

    #[must_use]
    pub fn title(&self) -> &CleanText {
        &self.title
    }

    #[must_use]
    pub fn goal(&self) -> &CleanText {
        &self.goal
    }

    #[must_use]
    pub fn status(&self) -> ProjectStatus {
        self.status
    }

    #[must_use]
    pub fn workspace(&self) -> &WorkspacePath {
        &self.workspace
    }

    #[must_use]
    pub fn budget(&self) -> &Budget {
        &self.budget
    }

    #[must_use]
    pub fn usage(&self) -> &Usage {
        &self.usage
    }

    #[must_use]
    pub fn created_at_ms(&self) -> u64 {
        self.created_at_ms
    }

    #[must_use]
    pub fn within_budget(&self) -> bool {
        self.budget.allows(&self.usage)
    }

    pub fn record_usage(&mut self, tokens: u64, seconds: u64) -> Result<(), DomainError> {
        self.usage.record(tokens, seconds)
    }

    pub fn transition(&mut self, next: ProjectStatus) -> Result<(), DomainError> {
        if !self.status.can_become(next) {
            return Err(DomainError::Transition {
                from: self.status.name(),
                to: next.name(),
            });
        }
        self.status = next;
        Ok(())
    }
}
