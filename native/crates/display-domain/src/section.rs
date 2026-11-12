use crate::error::DomainError;
use serde::{Deserialize, Serialize};

pub const MAX_SECTION_KEY: usize = 64;

#[derive(
    Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Default, Serialize, Deserialize,
)]
#[serde(transparent)]
pub struct Version(pub u64);

impl Version {
    #[must_use]
    pub const fn next(self) -> Self {
        Self(self.0.saturating_add(1))
    }
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(try_from = "String", into = "String")]
pub struct SectionKey(String);

impl SectionKey {
    pub fn parse(raw: &str) -> Result<Self, DomainError> {
        let valid = !raw.is_empty()
            && raw.len() <= MAX_SECTION_KEY
            && raw.bytes().all(|b| {
                b.is_ascii_lowercase() || b.is_ascii_digit() || matches!(b, b'_' | b'-' | b':')
            });
        if valid {
            Ok(Self(raw.to_owned()))
        } else {
            Err(DomainError::SectionKey)
        }
    }

    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl TryFrom<String> for SectionKey {
    type Error = DomainError;

    fn try_from(value: String) -> Result<Self, Self::Error> {
        Self::parse(&value)
    }
}

impl From<SectionKey> for String {
    fn from(value: SectionKey) -> Self {
        value.0
    }
}
