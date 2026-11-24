use std::fmt;

#[derive(Debug, PartialEq, Eq)]
pub enum ExecError {
    Journal(&'static str),
    UnknownStep(String),
    UnknownEntity(String),
    Cancelled,
}

pub type ExecResult<T> = Result<T, ExecError>;

impl fmt::Display for ExecError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Journal(what) => write!(f, "exec.journal.{what}"),
            Self::UnknownStep(id) => write!(f, "exec.unknown_step.{id}"),
            Self::UnknownEntity(role) => write!(f, "exec.unknown_entity.{role}"),
            Self::Cancelled => f.write_str("exec.cancelled"),
        }
    }
}

impl std::error::Error for ExecError {}
