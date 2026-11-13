use serde::{Deserialize, Serialize};

use crate::error::ContextError;

pub const MAX_ID: usize = 64;

#[derive(Clone, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(try_from = "String", into = "String")]
pub struct PersonId(String);

impl PersonId {
    pub fn new(text: &str) -> Result<Self, ContextError> {
        Self::try_from(text.to_owned())
    }

    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl TryFrom<String> for PersonId {
    type Error = ContextError;

    fn try_from(text: String) -> Result<Self, Self::Error> {
        let ok = !text.is_empty()
            && text.len() <= MAX_ID
            && text
                .bytes()
                .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || matches!(b, b'_' | b'-'));
        if ok {
            Ok(Self(text))
        } else {
            Err(ContextError::Invalid)
        }
    }
}

impl From<PersonId> for String {
    fn from(value: PersonId) -> Self {
        value.0
    }
}

impl std::fmt::Debug for PersonId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("PersonId(..)")
    }
}
