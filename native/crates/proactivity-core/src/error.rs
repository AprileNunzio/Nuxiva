#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ProactivityError {
    Parse,
    TooLarge,
    Invalid,
    Settings,
    Rules,
    NotFound,
    State,
    Consent,
    Expired,
    Serialize,
}

impl ProactivityError {
    const ALL: [Self; 10] = [
        Self::Parse,
        Self::TooLarge,
        Self::Invalid,
        Self::Settings,
        Self::Rules,
        Self::NotFound,
        Self::State,
        Self::Consent,
        Self::Expired,
        Self::Serialize,
    ];

    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Parse => "proactivity.parse",
            Self::TooLarge => "proactivity.too_large",
            Self::Invalid => "proactivity.invalid",
            Self::Settings => "proactivity.settings.invalid",
            Self::Rules => "proactivity.rules.invalid",
            Self::NotFound => "proactivity.not_found",
            Self::State => "proactivity.state",
            Self::Consent => "proactivity.consent",
            Self::Expired => "proactivity.expired",
            Self::Serialize => "proactivity.serialize",
        }
    }

    #[must_use]
    pub fn from_code(code: &str) -> Option<Self> {
        Self::ALL.into_iter().find(|e| e.code() == code)
    }
}

impl std::fmt::Display for ProactivityError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.code())
    }
}

impl std::error::Error for ProactivityError {}

pub type ProactivityResult<T> = Result<T, ProactivityError>;
