use serde::{Deserialize, Serialize};

use crate::error::DomainError;
use crate::text::CleanText;

const MAX_ID: usize = 64;
const MAX_TITLE: usize = 200;
const MAX_RATIONALE: usize = 4_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DecisionStatus {
    Proposed,
    Accepted,
    Rejected,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Decision {
    id: CleanText,
    title: CleanText,
    rationale: CleanText,
    status: DecisionStatus,
}

impl Decision {
    pub fn new(
        id: &str,
        title: &str,
        rationale: &str,
        status: DecisionStatus,
    ) -> Result<Self, DomainError> {
        Ok(Self {
            id: CleanText::new("id", id, MAX_ID)?,
            title: CleanText::new("title", title, MAX_TITLE)?,
            rationale: CleanText::new("rationale", rationale, MAX_RATIONALE)?,
            status,
        })
    }

    #[must_use]
    pub fn id(&self) -> &CleanText {
        &self.id
    }

    #[must_use]
    pub fn title(&self) -> &CleanText {
        &self.title
    }

    #[must_use]
    pub fn rationale(&self) -> &CleanText {
        &self.rationale
    }

    #[must_use]
    pub fn status(&self) -> DecisionStatus {
        self.status
    }

    pub fn set_status(&mut self, status: DecisionStatus) {
        self.status = status;
    }
}
