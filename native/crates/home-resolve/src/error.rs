use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ResolveError {
    TooLarge(&'static str),
    Invalid(String),
}

impl fmt::Display for ResolveError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::TooLarge(what) => write!(f, "home.resolve.too_large.{what}"),
            Self::Invalid(why) => write!(f, "home.resolve.invalid: {why}"),
        }
    }
}

impl std::error::Error for ResolveError {}

pub type ResolveResult<T> = Result<T, ResolveError>;
