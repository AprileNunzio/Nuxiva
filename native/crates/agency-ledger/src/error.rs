use thiserror::Error;

#[derive(Debug, Error)]
pub enum LedgerError {
    #[error("invalid event kind")]
    InvalidKind,
    #[error("payload exceeds {0} bytes")]
    PayloadTooLarge(usize),
    #[error("entry {0} breaks the sequence")]
    Sequence(u64),
    #[error("entry {0} does not link to the previous one")]
    Link(u64),
    #[error("entry {0} has an invalid signature")]
    Signature(u64),
    #[error("line {0} is malformed")]
    Malformed(u64),
    #[error("a previous write failed; reopen the ledger")]
    Poisoned,
    #[error("sequence counter exhausted")]
    Exhausted,
    #[error("io: {0}")]
    Io(#[from] std::io::Error),
    #[error("json: {0}")]
    Json(#[from] serde_json::Error),
}
