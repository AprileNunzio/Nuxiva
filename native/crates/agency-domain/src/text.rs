use std::fmt;

use serde::{Deserialize, Deserializer, Serialize, Serializer};

use crate::error::DomainError;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CleanText(String);

impl CleanText {
    pub fn new(field: &'static str, raw: &str, max_chars: usize) -> Result<Self, DomainError> {
        let cleaned: String = raw
            .chars()
            .map(|c| if c == '\t' || c == '\r' { ' ' } else { c })
            .filter(|c| *c == '\n' || !c.is_control())
            .filter(|c| !is_bidi_override(*c))
            .collect();
        let trimmed = cleaned.trim();
        if trimmed.is_empty() {
            return Err(DomainError::InvalidText {
                field,
                reason: "empty",
            });
        }
        if trimmed.chars().count() > max_chars {
            return Err(DomainError::InvalidText {
                field,
                reason: "too long",
            });
        }
        Ok(Self(trimmed.to_owned()))
    }

    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

fn is_bidi_override(c: char) -> bool {
    matches!(c, '\u{202A}'..='\u{202E}' | '\u{2066}'..='\u{2069}' | '\u{200E}' | '\u{200F}')
}

impl fmt::Display for CleanText {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

impl Serialize for CleanText {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        serializer.serialize_str(&self.0)
    }
}

impl<'de> Deserialize<'de> for CleanText {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        let raw = String::deserialize(deserializer)?;
        Self::new("text", &raw, 20_000).map_err(serde::de::Error::custom)
    }
}
