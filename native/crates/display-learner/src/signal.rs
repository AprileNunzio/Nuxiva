use nuxiva_display_planner::Size;
use serde::{Deserialize, Serialize};

use crate::context::ContextVector;
use crate::error::LearnError;

pub const MAX_WIDGET: usize = 64;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Kind {
    Shown,
    QuickClose,
    ClosedAfterUse,
    Interact,
    Dwell,
    Move,
    Resize,
    AskShow,
    AskHide,
    Expired,
}

impl Kind {
    #[must_use]
    pub const fn reward(self) -> (f32, f32) {
        match self {
            Self::QuickClose => (-1.0, 1.0),
            Self::Interact => (0.6, 1.0),
            Self::Dwell => (0.2, 0.5),
            Self::AskShow => (1.0, 1.5),
            Self::AskHide => (-1.0, 1.5),
            Self::Expired => (-0.3, 0.5),
            Self::Shown | Self::ClosedAfterUse | Self::Move | Self::Resize => (0.0, 0.0),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FeedbackSample {
    #[serde(default)]
    pub person: Option<String>,
    pub widget: String,
    pub kind: Kind,
    #[serde(default)]
    pub context: ContextVector,
    pub at_ms: u64,
    #[serde(default)]
    pub cell: Option<[u8; 2]>,
    #[serde(default)]
    pub size: Option<Size>,
    #[serde(default)]
    pub guests: bool,
    #[serde(default)]
    pub urgency: u8,
}

pub fn valid_widget(widget: &str) -> Result<(), LearnError> {
    let ok = !widget.is_empty()
        && widget.len() <= MAX_WIDGET
        && widget
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_' || b == b'-');
    if ok {
        Ok(())
    } else {
        Err(LearnError::InvalidWidget)
    }
}

pub fn valid_person(person: &str) -> Result<(), LearnError> {
    let ok = (32..=128).contains(&person.len()) && person.bytes().all(|b| b.is_ascii_hexdigit());
    if ok {
        Ok(())
    } else {
        Err(LearnError::InvalidPerson)
    }
}

impl FeedbackSample {
    pub fn validate(&self) -> Result<(), LearnError> {
        valid_widget(&self.widget)?;
        if let Some(person) = &self.person {
            valid_person(person)?;
        }
        if self.cell.is_some_and(|[col, row]| col >= 12 || row >= 48) {
            return Err(LearnError::InvalidSample);
        }
        Ok(())
    }
}
