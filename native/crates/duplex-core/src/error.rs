#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DuplexError {
    Parse,
    TooLarge,
    Invalid,
    Settings,
    Version,
    Sequence,
    Stale,
    RateLimited,
    Transition,
    Capacity,
    Serialize,
}

impl DuplexError {
    pub const ALL: [Self; 11] = [
        Self::Parse,
        Self::TooLarge,
        Self::Invalid,
        Self::Settings,
        Self::Version,
        Self::Sequence,
        Self::Stale,
        Self::RateLimited,
        Self::Transition,
        Self::Capacity,
        Self::Serialize,
    ];

    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Parse => "duplex.parse",
            Self::TooLarge => "duplex.too_large",
            Self::Invalid => "duplex.invalid",
            Self::Settings => "duplex.settings.invalid",
            Self::Version => "duplex.version",
            Self::Sequence => "duplex.sequence",
            Self::Stale => "duplex.stale",
            Self::RateLimited => "duplex.rate_limited",
            Self::Transition => "duplex.transition",
            Self::Capacity => "duplex.capacity",
            Self::Serialize => "duplex.serialize",
        }
    }
}

impl std::fmt::Display for DuplexError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.code())
    }
}

impl std::error::Error for DuplexError {}

pub type DuplexResult<T> = Result<T, DuplexError>;
