use thiserror::Error;

#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum DomainError {
    #[error("invalid identifier: {0}")]
    InvalidId(String),
    #[error("invalid text for {field}: {reason}")]
    InvalidText {
        field: &'static str,
        reason: &'static str,
    },
    #[error("invalid workspace path: {0}")]
    InvalidWorkspace(&'static str),
    #[error("invalid budget: {0}")]
    InvalidBudget(&'static str),
    #[error("transition {from} -> {to} is not allowed")]
    Transition {
        from: &'static str,
        to: &'static str,
    },
    #[error("attempt limit reached")]
    AttemptsExhausted,
    #[error("usage counter overflow")]
    Overflow,
}
