#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LoopError {
    Parse,
    TooLarge,
    Invalid,
    Version,
    Settings,
    Path,
    Protected,
    Digest,
    Report,
    Coder,
    Critic,
    Serialize,
}

impl LoopError {
    const ALL: [Self; 12] = [
        Self::Parse,
        Self::TooLarge,
        Self::Invalid,
        Self::Version,
        Self::Settings,
        Self::Path,
        Self::Protected,
        Self::Digest,
        Self::Report,
        Self::Coder,
        Self::Critic,
        Self::Serialize,
    ];

    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Parse => "loop.parse",
            Self::TooLarge => "loop.too_large",
            Self::Invalid => "loop.invalid",
            Self::Version => "loop.version",
            Self::Settings => "loop.settings.invalid",
            Self::Path => "loop.path",
            Self::Protected => "loop.protected",
            Self::Digest => "loop.digest",
            Self::Report => "loop.report",
            Self::Coder => "loop.coder",
            Self::Critic => "loop.critic",
            Self::Serialize => "loop.serialize",
        }
    }

    #[must_use]
    pub fn from_code(code: &str) -> Option<Self> {
        Self::ALL.into_iter().find(|e| e.code() == code)
    }
}

impl std::fmt::Display for LoopError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.code())
    }
}

impl std::error::Error for LoopError {}

pub type LoopResult<T> = Result<T, LoopError>;
