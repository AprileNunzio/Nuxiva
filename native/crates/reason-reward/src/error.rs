use std::fmt;

#[derive(Debug)]
pub enum RewardError {
    Invalid(&'static str),
    Full,
    Json(serde_json::Error),
}

pub type RewardResult<T> = Result<T, RewardError>;

impl fmt::Display for RewardError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Invalid(what) => write!(f, "reward.invalid.{what}"),
            Self::Full => f.write_str("reward.full"),
            Self::Json(_) => f.write_str("reward.json"),
        }
    }
}

impl std::error::Error for RewardError {}

impl From<serde_json::Error> for RewardError {
    fn from(value: serde_json::Error) -> Self {
        Self::Json(value)
    }
}
