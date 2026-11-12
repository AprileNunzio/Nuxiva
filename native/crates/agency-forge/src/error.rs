use thiserror::Error;

#[derive(Debug, Error, PartialEq, Eq)]
pub enum ForgeError {
    #[error("invalid tool name '{0}': must be lowercase alphanumeric/underscore (3..=40 chars)")]
    InvalidName(String),
    #[error("source guard rejected tool: {0}")]
    GuardRejected(String),
    #[error("invalid test suite: {0}")]
    InvalidTests(String),
    #[error("tool '{0}' already exists")]
    AlreadyExists(String),
    #[error("tool '{0}' not found")]
    NotFound(String),
    #[error("tool '{0}' is not approved or has been revoked")]
    NotCallable(String),
    #[error("catalog capacity reached ({0})")]
    CapacityReached(usize),
}
