use thiserror::Error;

use crate::{IndexError, ScanError};

#[derive(Debug, Error)]
pub enum BenchError {
    #[error("invalid configuration: {0}")]
    Config(&'static str),
    #[error("corpus root must not exist or must be empty")]
    RootNotEmpty,
    #[error("io: {0}")]
    Io(#[from] std::io::Error),
    #[error("scan: {0}")]
    Scan(#[from] ScanError),
    #[error("index: {0}")]
    Index(#[from] IndexError),
    #[error("json: {0}")]
    Json(#[from] serde_json::Error),
}
