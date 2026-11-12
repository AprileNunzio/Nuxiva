use agency_domain::DomainError;
use agency_planner::PlanError;
use thiserror::Error;

#[derive(Debug, Error, PartialEq, Eq)]
pub enum ThoughtError {
    #[error("empty candidates list")]
    EmptyCandidates,
    #[error("too many candidates: limit is {0}")]
    TooManyCandidates(usize),
    #[error("invalid identifier '{0}'")]
    InvalidIdentifier(String),
    #[error("invalid text in field '{field}': {reason}")]
    InvalidText {
        field: &'static str,
        reason: &'static str,
    },
    #[error("contract conflict on '{id}': {reason}")]
    ContractConflict { id: String, reason: String },
    #[error("contract not found: '{0}'")]
    ContractNotFound(String),
    #[error("decomposition failed: {0}")]
    Decomposition(String),
    #[error(transparent)]
    Domain(#[from] DomainError),
    #[error(transparent)]
    Plan(#[from] PlanError),
}
