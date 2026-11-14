#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum InitiativeError {
    Parse,
    TooLarge,
    Invalid,
    Settings,
    Catalog,
    NotFound,
    State,
    Consent,
    Serialize,
}

impl InitiativeError {
    const ALL: [Self; 9] = [
        Self::Parse,
        Self::TooLarge,
        Self::Invalid,
        Self::Settings,
        Self::Catalog,
        Self::NotFound,
        Self::State,
        Self::Consent,
        Self::Serialize,
    ];

    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Parse => "initiative.parse",
            Self::TooLarge => "initiative.too_large",
            Self::Invalid => "initiative.invalid",
            Self::Settings => "initiative.settings.invalid",
            Self::Catalog => "initiative.catalog.invalid",
            Self::NotFound => "initiative.not_found",
            Self::State => "initiative.state",
            Self::Consent => "initiative.consent",
            Self::Serialize => "initiative.serialize",
        }
    }

    #[must_use]
    pub fn from_code(code: &str) -> Option<Self> {
        Self::ALL.into_iter().find(|e| e.code() == code)
    }
}

impl std::fmt::Display for InitiativeError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.code())
    }
}

impl std::error::Error for InitiativeError {}

pub type InitiativeResult<T> = Result<T, InitiativeError>;
