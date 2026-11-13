#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ContextError {
    Invalid,
    TooLarge,
    Settings,
    Seal,
    Unknown,
    Capacity,
}

impl ContextError {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Invalid => "context.invalid",
            Self::TooLarge => "context.too_large",
            Self::Settings => "context.settings.invalid",
            Self::Seal => "context.seal",
            Self::Unknown => "context.unknown",
            Self::Capacity => "context.capacity",
        }
    }
}

impl std::fmt::Display for ContextError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.code())
    }
}

impl std::error::Error for ContextError {}

pub type ContextResult<T> = Result<T, ContextError>;
