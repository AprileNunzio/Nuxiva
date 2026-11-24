use std::fmt;

#[derive(Debug)]
pub enum EvalError {
    Invalid(&'static str),
    Duplicate(String),
    Missing(String),
    Io(std::io::Error),
    Json(serde_json::Error),
    Bench(bench_core::BenchError),
}

pub type EvalResult<T> = Result<T, EvalError>;

impl fmt::Display for EvalError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Invalid(what) => write!(f, "eval.invalid.{what}"),
            Self::Duplicate(id) => write!(f, "eval.duplicate.{id}"),
            Self::Missing(id) => write!(f, "eval.missing.{id}"),
            Self::Io(_) => f.write_str("eval.io"),
            Self::Json(_) => f.write_str("eval.json"),
            Self::Bench(_) => f.write_str("eval.bench"),
        }
    }
}

impl std::error::Error for EvalError {}

impl From<std::io::Error> for EvalError {
    fn from(value: std::io::Error) -> Self {
        Self::Io(value)
    }
}

impl From<serde_json::Error> for EvalError {
    fn from(value: serde_json::Error) -> Self {
        Self::Json(value)
    }
}

impl From<bench_core::BenchError> for EvalError {
    fn from(value: bench_core::BenchError) -> Self {
        Self::Bench(value)
    }
}
