use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AccessError {
    Capability,
    Cell,
    Schema,
    Version,
    TooLarge,
}

impl AccessError {
    #[must_use]
    pub const fn code(&self) -> &'static str {
        match self {
            Self::Capability => "access.error.capability",
            Self::Cell => "access.error.cell",
            Self::Schema => "access.error.schema",
            Self::Version => "access.error.version",
            Self::TooLarge => "access.error.too_large",
        }
    }
}

impl fmt::Display for AccessError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.code())
    }
}

impl std::error::Error for AccessError {}
