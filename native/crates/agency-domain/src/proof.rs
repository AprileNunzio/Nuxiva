use serde::{Deserialize, Serialize};

use crate::error::DomainError;
use crate::text::CleanText;

const MAX_PROOF_CRITERION: usize = 500;
const MAX_PROOF_COMMAND: usize = 1_000;
const MAX_PROOF_OUTPUT: usize = 16_000;
const MAX_HASH: usize = 128;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Proof {
    criterion: CleanText,
    command: CleanText,
    expected_output: CleanText,
    #[serde(default)]
    actual_output: Option<CleanText>,
    #[serde(default)]
    verified: bool,
    #[serde(default)]
    artifact_hash: Option<CleanText>,
}

impl Proof {
    pub fn new(criterion: &str, command: &str, expected_output: &str) -> Result<Self, DomainError> {
        Ok(Self {
            criterion: CleanText::new("criterion", criterion, MAX_PROOF_CRITERION)?,
            command: CleanText::new("command", command, MAX_PROOF_COMMAND)?,
            expected_output: CleanText::new("expected_output", expected_output, MAX_PROOF_OUTPUT)?,
            actual_output: None,
            verified: false,
            artifact_hash: None,
        })
    }

    #[must_use]
    pub fn criterion(&self) -> &CleanText {
        &self.criterion
    }

    #[must_use]
    pub fn command(&self) -> &CleanText {
        &self.command
    }

    #[must_use]
    pub fn expected_output(&self) -> &CleanText {
        &self.expected_output
    }

    #[must_use]
    pub fn actual_output(&self) -> Option<&CleanText> {
        self.actual_output.as_ref()
    }

    #[must_use]
    pub fn is_verified(&self) -> bool {
        self.verified
    }

    #[must_use]
    pub fn artifact_hash(&self) -> Option<&CleanText> {
        self.artifact_hash.as_ref()
    }

    pub fn record_result(
        &mut self,
        actual_output: &str,
        artifact_hash: Option<&str>,
        verified: bool,
    ) -> Result<(), DomainError> {
        self.actual_output = Some(CleanText::new(
            "actual_output",
            actual_output,
            MAX_PROOF_OUTPUT,
        )?);
        self.artifact_hash = match artifact_hash {
            Some(h) => Some(CleanText::new("artifact_hash", h, MAX_HASH)?),
            None => None,
        };
        self.verified = verified;
        Ok(())
    }
}
