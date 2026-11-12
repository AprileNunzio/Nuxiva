use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum NvrError {
    InvalidId,
    InvalidSegment,
    NotFound,
    TooMany,
    Serialization(String),
}

impl NvrError {
    #[must_use]
    pub const fn code(&self) -> &'static str {
        match self {
            Self::InvalidId => "nvr.id.invalid",
            Self::InvalidSegment => "nvr.segment.invalid",
            Self::NotFound => "nvr.segment.not_found",
            Self::TooMany => "nvr.catalog.too_many",
            Self::Serialization(_) => "nvr.catalog.corrupt",
        }
    }
}

impl fmt::Display for NvrError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.code())
    }
}

impl std::error::Error for NvrError {}

pub type NvrResult<T> = Result<T, NvrError>;
