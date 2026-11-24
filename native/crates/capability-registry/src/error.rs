use std::fmt;

#[derive(Debug)]
pub enum RegistryError {
    Invalid(&'static str),
    Duplicate(String),
    Unknown(String),
    TooLarge,
    Json(serde_json::Error),
}

pub type RegistryResult<T> = Result<T, RegistryError>;

impl fmt::Display for RegistryError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Invalid(what) => write!(f, "capability.invalid.{what}"),
            Self::Duplicate(id) => write!(f, "capability.duplicate.{id}"),
            Self::Unknown(id) => write!(f, "capability.unknown.{id}"),
            Self::TooLarge => f.write_str("capability.too_large"),
            Self::Json(_) => f.write_str("capability.json"),
        }
    }
}

impl std::error::Error for RegistryError {}

impl From<serde_json::Error> for RegistryError {
    fn from(value: serde_json::Error) -> Self {
        Self::Json(value)
    }
}
