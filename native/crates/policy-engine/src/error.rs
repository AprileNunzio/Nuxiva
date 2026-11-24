use std::fmt;

#[derive(Debug, PartialEq, Eq)]
pub enum PolicyError {
    Invalid(&'static str),
    TooLarge,
}

pub type PolicyResult<T> = Result<T, PolicyError>;

impl fmt::Display for PolicyError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Invalid(what) => write!(f, "policy.invalid.{what}"),
            Self::TooLarge => f.write_str("policy.too_large"),
        }
    }
}

impl std::error::Error for PolicyError {}
