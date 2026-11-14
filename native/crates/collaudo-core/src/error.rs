use std::fmt;

#[derive(Debug)]
pub enum CollaudoError {
    Invalid(&'static str),
    Io(std::io::Error),
    Json(serde_json::Error),
    Random,
    Poisoned,
    Corrupt(&'static str),
}

impl fmt::Display for CollaudoError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Invalid(what) => write!(f, "collaudo.invalid.{what}"),
            Self::Io(_) => f.write_str("collaudo.io"),
            Self::Json(_) => f.write_str("collaudo.json"),
            Self::Random => f.write_str("collaudo.random"),
            Self::Poisoned => f.write_str("collaudo.poisoned"),
            Self::Corrupt(what) => write!(f, "collaudo.corrupt.{what}"),
        }
    }
}

impl std::error::Error for CollaudoError {}

impl From<std::io::Error> for CollaudoError {
    fn from(value: std::io::Error) -> Self {
        Self::Io(value)
    }
}

impl From<serde_json::Error> for CollaudoError {
    fn from(value: serde_json::Error) -> Self {
        Self::Json(value)
    }
}
