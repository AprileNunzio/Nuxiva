use std::fmt;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HoloError {
    TooLarge,
    BadJson,
    NoParts,
}

pub type HoloResult<T> = Result<T, HoloError>;

impl HoloError {
    #[must_use]
    pub fn code(self) -> &'static str {
        match self {
            Self::TooLarge => "holo_too_large",
            Self::BadJson => "holo_bad_json",
            Self::NoParts => "holo_no_parts",
        }
    }
}

impl fmt::Display for HoloError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.code())
    }
}

impl std::error::Error for HoloError {}
