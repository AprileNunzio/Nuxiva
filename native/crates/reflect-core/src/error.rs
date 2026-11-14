#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ReflectError {
    Parse,
    TooLarge,
    Invalid,
    Version,
    Settings,
    Catalog,
    UnknownKind,
    BadValue,
    NotFound,
    State,
    Blocked,
    Serialize,
}

impl ReflectError {
    const ALL: [Self; 12] = [
        Self::Parse,
        Self::TooLarge,
        Self::Invalid,
        Self::Version,
        Self::Settings,
        Self::Catalog,
        Self::UnknownKind,
        Self::BadValue,
        Self::NotFound,
        Self::State,
        Self::Blocked,
        Self::Serialize,
    ];

    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Parse => "reflect.parse",
            Self::TooLarge => "reflect.too_large",
            Self::Invalid => "reflect.invalid",
            Self::Version => "reflect.version",
            Self::Settings => "reflect.settings.invalid",
            Self::Catalog => "reflect.catalog.invalid",
            Self::UnknownKind => "reflect.unknown_kind",
            Self::BadValue => "reflect.bad_value",
            Self::NotFound => "reflect.not_found",
            Self::State => "reflect.state",
            Self::Blocked => "reflect.blocked",
            Self::Serialize => "reflect.serialize",
        }
    }

    #[must_use]
    pub fn from_code(code: &str) -> Option<Self> {
        Self::ALL.into_iter().find(|e| e.code() == code)
    }
}

impl std::fmt::Display for ReflectError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.code())
    }
}

impl std::error::Error for ReflectError {}

pub type ReflectResult<T> = Result<T, ReflectError>;
