use std::fmt;

#[derive(Debug, PartialEq, Eq)]
pub enum UnderstandError {
    Invalid(&'static str),
    Rejected(&'static str),
    Model(String),
    Exhausted,
}

pub type UnderstandResult<T> = Result<T, UnderstandError>;

impl fmt::Display for UnderstandError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Invalid(what) => write!(f, "understand.invalid.{what}"),
            Self::Rejected(what) => write!(f, "understand.rejected.{what}"),
            Self::Model(_) => f.write_str("understand.model"),
            Self::Exhausted => f.write_str("understand.exhausted"),
        }
    }
}

impl std::error::Error for UnderstandError {}
