use serde::{Deserialize, Serialize};

use crate::error::DomainError;
use crate::text::CleanText;

const MAX_ID: usize = 64;
const MAX_PROMPT: usize = 2_000;
const MAX_LABEL: usize = 200;
const MAX_DESCRIPTION: usize = 1_000;
const MAX_ANSWER: usize = 4_000;
const MAX_OPTIONS: usize = 16;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct QuestionOption {
    id: CleanText,
    label: CleanText,
    description: Option<CleanText>,
}

impl QuestionOption {
    pub fn new(id: &str, label: &str, description: Option<&str>) -> Result<Self, DomainError> {
        let desc = match description {
            Some(d) => Some(CleanText::new("description", d, MAX_DESCRIPTION)?),
            None => None,
        };
        Ok(Self {
            id: CleanText::new("id", id, MAX_ID)?,
            label: CleanText::new("label", label, MAX_LABEL)?,
            description: desc,
        })
    }

    #[must_use]
    pub fn id(&self) -> &CleanText {
        &self.id
    }

    #[must_use]
    pub fn label(&self) -> &CleanText {
        &self.label
    }

    #[must_use]
    pub fn description(&self) -> Option<&CleanText> {
        self.description.as_ref()
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Question {
    id: CleanText,
    prompt: CleanText,
    options: Vec<QuestionOption>,
    selected_option: Option<CleanText>,
    answer: Option<CleanText>,
}

impl Question {
    pub fn new(id: &str, prompt: &str, options: Vec<QuestionOption>) -> Result<Self, DomainError> {
        if options.len() > MAX_OPTIONS {
            return Err(DomainError::InvalidText {
                field: "options",
                reason: "too many options",
            });
        }
        Ok(Self {
            id: CleanText::new("id", id, MAX_ID)?,
            prompt: CleanText::new("prompt", prompt, MAX_PROMPT)?,
            options,
            selected_option: None,
            answer: None,
        })
    }

    #[must_use]
    pub fn id(&self) -> &CleanText {
        &self.id
    }

    #[must_use]
    pub fn prompt(&self) -> &CleanText {
        &self.prompt
    }

    #[must_use]
    pub fn options(&self) -> &[QuestionOption] {
        &self.options
    }

    #[must_use]
    pub fn selected_option(&self) -> Option<&CleanText> {
        self.selected_option.as_ref()
    }

    #[must_use]
    pub fn answer_text(&self) -> Option<&CleanText> {
        self.answer.as_ref()
    }

    #[must_use]
    pub fn is_answered(&self) -> bool {
        self.selected_option.is_some() || self.answer.is_some()
    }

    pub fn answer(
        &mut self,
        selected_option: Option<&str>,
        answer: Option<&str>,
    ) -> Result<(), DomainError> {
        if let Some(opt) = selected_option {
            if !self.options.is_empty() && !self.options.iter().any(|o| o.id().as_str() == opt) {
                return Err(DomainError::InvalidText {
                    field: "selected_option",
                    reason: "option not recognized",
                });
            }
            self.selected_option = Some(CleanText::new("selected_option", opt, MAX_ID)?);
        }
        if let Some(ans) = answer {
            self.answer = Some(CleanText::new("answer", ans, MAX_ANSWER)?);
        }
        Ok(())
    }
}
