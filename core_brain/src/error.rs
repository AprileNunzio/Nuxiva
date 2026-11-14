use std::fmt;

use nuxiva_context_core::ContextError;
use nuxiva_ear_core::aec::AecError;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BrainError {
    Aec(AecError),
    Context(String),
    Embedding(&'static str),
    Input(&'static str),
    QueueFull,
    Closed,
    Panic,
    Deadline,
}

pub type BrainResult<T> = Result<T, BrainError>;

impl fmt::Display for BrainError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Aec(e) => write!(f, "brain.aec.{e}"),
            Self::Context(e) => write!(f, "brain.context.{e}"),
            Self::Embedding(e) => write!(f, "brain.embedding.{e}"),
            Self::Input(e) => write!(f, "brain.input.{e}"),
            Self::QueueFull => f.write_str("brain.queue.full"),
            Self::Closed => f.write_str("brain.closed"),
            Self::Panic => f.write_str("brain.panic"),
            Self::Deadline => f.write_str("brain.deadline"),
        }
    }
}

impl std::error::Error for BrainError {}

impl From<AecError> for BrainError {
    fn from(value: AecError) -> Self {
        Self::Aec(value)
    }
}

impl From<ContextError> for BrainError {
    fn from(value: ContextError) -> Self {
        Self::Context(format!("{value:?}"))
    }
}
