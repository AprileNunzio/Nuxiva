use std::fmt;

use serde::{Deserialize, Deserializer, Serialize, Serializer};

use crate::error::DomainError;

const MAX_ID_LEN: usize = 64;

fn validate(raw: &str) -> Result<String, DomainError> {
    let valid_char = |c: char| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '-' || c == '_';
    let starts_ok = raw
        .chars()
        .next()
        .is_some_and(|c| c.is_ascii_lowercase() || c.is_ascii_digit());
    if raw.is_empty() || raw.len() > MAX_ID_LEN || !starts_ok || !raw.chars().all(valid_char) {
        return Err(DomainError::InvalidId(
            raw.chars().take(MAX_ID_LEN).collect(),
        ));
    }
    Ok(raw.to_owned())
}

macro_rules! slug_id {
    ($name:ident) => {
        #[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
        pub struct $name(String);

        impl $name {
            pub fn new(raw: &str) -> Result<Self, DomainError> {
                validate(raw).map(Self)
            }

            #[must_use]
            pub fn as_str(&self) -> &str {
                &self.0
            }
        }

        impl fmt::Display for $name {
            fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
                f.write_str(&self.0)
            }
        }

        impl Serialize for $name {
            fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
                serializer.serialize_str(&self.0)
            }
        }

        impl<'de> Deserialize<'de> for $name {
            fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
                let raw = String::deserialize(deserializer)?;
                Self::new(&raw).map_err(serde::de::Error::custom)
            }
        }
    };
}

slug_id!(ProjectId);
slug_id!(TaskId);
slug_id!(RoleId);
