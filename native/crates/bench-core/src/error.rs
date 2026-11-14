use std::fmt;

#[derive(Debug)]
pub enum BenchError {
    Invalid(&'static str),
    TooLarge(&'static str),
    Corrupt(&'static str),
    Io(std::io::Error),
    Json(serde_json::Error),
}

pub type BenchResult<T> = Result<T, BenchError>;

impl fmt::Display for BenchError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Invalid(what) => write!(f, "bench.invalid.{what}"),
            Self::TooLarge(what) => write!(f, "bench.too_large.{what}"),
            Self::Corrupt(what) => write!(f, "bench.corrupt.{what}"),
            Self::Io(_) => f.write_str("bench.io"),
            Self::Json(_) => f.write_str("bench.json"),
        }
    }
}

impl std::error::Error for BenchError {}

impl From<std::io::Error> for BenchError {
    fn from(value: std::io::Error) -> Self {
        Self::Io(value)
    }
}

impl From<serde_json::Error> for BenchError {
    fn from(value: serde_json::Error) -> Self {
        Self::Json(value)
    }
}
