use thiserror::Error;

#[derive(Debug, Error, PartialEq, Eq, Clone)]
pub enum TernaryError {
    #[error("dimension mismatch: expected {expected}, got {actual}")]
    DimensionMismatch { expected: usize, actual: usize },
    #[error("invalid bitmask: positive and negative masks overlap at word index {index}")]
    OverlappingMasks { index: usize },
    #[error("empty vector is not allowed")]
    EmptyVector,
    #[error("invalid trit value: {value}")]
    InvalidTrit { value: i8 },
    #[error("invalid threshold factor: {factor}")]
    InvalidThreshold { factor: String },
    #[error("cluster not found: {id}")]
    ClusterNotFound { id: u64 },
    #[error("node not found: {id}")]
    NodeNotFound { id: String },
    #[error("invalid retention parameter: {reason}")]
    InvalidRetentionParameter { reason: String },
    #[error("hydration failed for {id}: {reason}")]
    HydrationFailed { id: String, reason: String },
}
