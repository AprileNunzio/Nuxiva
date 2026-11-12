use thiserror::Error;

#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum ForesightError {
    #[error("invalid {field}: {reason}")]
    Invalid {
        field: &'static str,
        reason: &'static str,
    },
    #[error("duplicate key in {0}")]
    Duplicate(&'static str),
    #[error("unknown reference in {0}")]
    Unknown(&'static str),
    #[error("limit exceeded: {0}")]
    Limit(&'static str),
    #[error("simulation already finished")]
    Finished,
    #[error("agent not found")]
    AgentNotFound,
    #[error("snapshot does not match its scenario")]
    Corrupt,
}
