use serde::{Deserialize, Serialize};

use crate::error::{RewardError, RewardResult};

pub const MAX_TESTS: u32 = 1_000_000;
pub const MAX_ISSUES: u32 = 10_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum StepOutcome {
    Done,
    Replayed,
    Failed,
    Indeterminate,
    Missing,
    Skipped,
    Cancelled,
    Denied,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum Signal {
    Tests {
        passed: u32,
        total: u32,
    },
    Command {
        exit_code: i32,
        timed_out: bool,
    },
    Document {
        valid: bool,
        issues: u32,
    },
    Step {
        outcome: StepOutcome,
    },
    Intent {
        matched: bool,
        completed: bool,
        wrong_action: bool,
    },
}

impl Signal {
    pub fn validate(&self) -> RewardResult<()> {
        match *self {
            Self::Tests { passed, total } if total == 0 || total > MAX_TESTS || passed > total => {
                Err(RewardError::Invalid("tests"))
            }
            Self::Document { issues, .. } if issues > MAX_ISSUES => {
                Err(RewardError::Invalid("document"))
            }
            Self::Intent {
                matched: true,
                completed: false,
                ..
            } => Err(RewardError::Invalid("intent")),
            _ => Ok(()),
        }
    }

    #[must_use]
    pub fn is_unsafe(&self) -> bool {
        matches!(
            self,
            Self::Intent {
                wrong_action: true,
                ..
            }
        )
    }
}
