use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CheckinError {
    TooLarge(&'static str),
    Invalid(String),
}

impl fmt::Display for CheckinError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::TooLarge(what) => write!(f, "checkin.too_large.{what}"),
            Self::Invalid(why) => write!(f, "checkin.invalid: {why}"),
        }
    }
}

impl std::error::Error for CheckinError {}

pub type CheckinResult<T> = Result<T, CheckinError>;
