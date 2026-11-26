use std::fmt;

#[derive(Debug)]
pub enum FitError {
    Invalid(&'static str),
    NoFit,
    Json(serde_json::Error),
}

pub type FitResult<T> = Result<T, FitError>;

impl fmt::Display for FitError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Invalid(what) => write!(f, "fit.invalid.{what}"),
            Self::NoFit => f.write_str("fit.no_fit"),
            Self::Json(_) => f.write_str("fit.json"),
        }
    }
}

impl std::error::Error for FitError {}

impl From<serde_json::Error> for FitError {
    fn from(value: serde_json::Error) -> Self {
        Self::Json(value)
    }
}
