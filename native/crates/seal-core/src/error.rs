#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SealError {
    Key,
    Token,
    TooLarge,
    Random,
}

impl SealError {
    #[must_use]
    pub fn code(self) -> &'static str {
        match self {
            Self::Key => "seal.key.invalid",
            Self::Token => "seal.token.invalid",
            Self::TooLarge => "seal.too_large",
            Self::Random => "seal.random.unavailable",
        }
    }
}

impl std::fmt::Display for SealError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.code())
    }
}

impl std::error::Error for SealError {}

pub type SealResult<T> = Result<T, SealError>;
