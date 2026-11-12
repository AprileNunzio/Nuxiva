use serde::Serialize;
use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize)]
#[serde(transparent)]
pub struct Revision(String);

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct InvalidRevision;

impl fmt::Display for InvalidRevision {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("invalid_revision")
    }
}

impl std::error::Error for InvalidRevision {}

impl Revision {
    pub fn parse(raw: &str) -> Result<Self, InvalidRevision> {
        let value = raw.trim();
        let valid_len = value.len() == 40 || value.len() == 64;
        if valid_len
            && value
                .bytes()
                .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
        {
            Ok(Self(value.to_owned()))
        } else {
            Err(InvalidRevision)
        }
    }

    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }

    #[must_use]
    pub fn short(&self) -> &str {
        self.0.get(..7).unwrap_or(&self.0)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn accepts_sha1_and_sha256_lowercase() {
        let sha1 = "a".repeat(40);
        let sha256 = "0f".repeat(32);
        assert!(Revision::parse(&sha1).is_ok());
        assert!(Revision::parse(&sha256).is_ok());
        assert_eq!(Revision::parse(&sha1).map(|r| r.short().len()), Ok(7));
    }

    #[test]
    fn rejects_short_uppercase_and_injection() {
        assert!(Revision::parse("abc123").is_err());
        assert!(Revision::parse(&"A".repeat(40)).is_err());
        assert!(Revision::parse(&format!("{}--", "a".repeat(38))).is_err());
        assert!(Revision::parse("HEAD").is_err());
    }
}
