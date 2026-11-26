use std::fmt;

#[derive(Debug, PartialEq, Eq)]
pub enum EngineError {
    Config(&'static str),
    Registry(String),
    Goal(String),
    Plan(String),
    Ledger(&'static str),
    Mode(&'static str),
}

pub type EngineResult<T> = Result<T, EngineError>;

impl fmt::Display for EngineError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Config(what) => write!(f, "reason.config.{what}"),
            Self::Registry(what) => write!(f, "reason.registry.{what}"),
            Self::Goal(what) => write!(f, "reason.goal.{what}"),
            Self::Plan(what) => write!(f, "reason.{what}"),
            Self::Ledger(what) => write!(f, "reason.ledger.{what}"),
            Self::Mode(what) => write!(f, "reason.mode.{what}"),
        }
    }
}

impl std::error::Error for EngineError {}
