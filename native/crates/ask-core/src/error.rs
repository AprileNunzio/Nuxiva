use std::fmt;

#[derive(Debug, PartialEq, Eq)]
pub enum AskError {
    EmptyQuery,
    ParseFailure(&'static str),
    RangeInvalid,
    SerializationError,
}

impl fmt::Display for AskError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::EmptyQuery => write!(f, "empty_query"),
            Self::ParseFailure(reason) => write!(f, "parse_failure: {reason}"),
            Self::RangeInvalid => write!(f, "range_invalid"),
            Self::SerializationError => write!(f, "serialization_error"),
        }
    }
}

impl std::error::Error for AskError {}
