use serde::{Deserialize, Serialize};

use crate::error::SwarmError;
use crate::limits::Ceilings;

#[must_use]
pub fn valid_token(text: &str, max: usize) -> bool {
    !text.is_empty()
        && text.len() <= max
        && text.bytes().all(|b| {
            b.is_ascii_lowercase() || b.is_ascii_digit() || matches!(b, b'_' | b'.' | b':' | b'-')
        })
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(try_from = "String", into = "String")]
pub struct Ident(String);

impl Ident {
    pub fn new(text: &str) -> Result<Self, SwarmError> {
        Self::try_from(text.to_owned())
    }

    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl TryFrom<String> for Ident {
    type Error = SwarmError;

    fn try_from(text: String) -> Result<Self, Self::Error> {
        if valid_token(&text, Ceilings::IDENT) {
            Ok(Self(text))
        } else {
            Err(SwarmError::Invalid)
        }
    }
}

impl From<Ident> for String {
    fn from(value: Ident) -> Self {
        value.0
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(try_from = "String", into = "String")]
pub struct Digest(String);

impl Digest {
    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }

    pub(crate) fn from_hex(text: String) -> Self {
        Self(text)
    }
}

impl TryFrom<String> for Digest {
    type Error = SwarmError;

    fn try_from(text: String) -> Result<Self, Self::Error> {
        let ok = text.len() == 64
            && text
                .bytes()
                .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b));
        if ok {
            Ok(Self(text))
        } else {
            Err(SwarmError::Invalid)
        }
    }
}

impl From<Digest> for String {
    fn from(value: Digest) -> Self {
        value.0
    }
}
