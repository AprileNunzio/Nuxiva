use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::error::{ReflectError, ReflectResult};
use crate::settings::MAX_PAYLOAD;

#[must_use]
pub fn name_ok(text: &str) -> bool {
    !text.is_empty()
        && text.len() <= 64
        && text.bytes().all(|b| {
            b.is_ascii_lowercase() || b.is_ascii_digit() || matches!(b, b'.' | b'_' | b'-')
        })
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct KindSpec {
    pub domain: String,
    pub max_value_len: usize,
    #[serde(default)]
    pub allowed_values: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Catalog {
    pub kinds: BTreeMap<String, KindSpec>,
}

impl Catalog {
    pub fn validate(&self) -> ReflectResult<()> {
        let ok = !self.kinds.is_empty()
            && self.kinds.len() <= 1_024
            && self.kinds.iter().all(|(k, s)| {
                name_ok(k)
                    && name_ok(&s.domain)
                    && (1..=256).contains(&s.max_value_len)
                    && s.allowed_values.len() <= 256
                    && s.allowed_values.iter().all(|v| {
                        !v.is_empty()
                            && v.chars().count() <= s.max_value_len
                            && !v.chars().any(char::is_control)
                    })
            });
        if ok {
            Ok(())
        } else {
            Err(ReflectError::Catalog)
        }
    }

    pub fn from_json(text: &str) -> ReflectResult<Self> {
        if text.len() > MAX_PAYLOAD {
            return Err(ReflectError::TooLarge);
        }
        let catalog: Self = serde_json::from_str(text).map_err(|_| ReflectError::Catalog)?;
        catalog.validate()?;
        Ok(catalog)
    }

    pub fn check(&self, kind: &str, value: &str) -> ReflectResult<&KindSpec> {
        let spec = self.kinds.get(kind).ok_or(ReflectError::UnknownKind)?;
        let ok = !value.is_empty()
            && value.chars().count() <= spec.max_value_len
            && !value.chars().any(char::is_control)
            && (spec.allowed_values.is_empty() || spec.allowed_values.iter().any(|v| v == value));
        if ok {
            Ok(spec)
        } else {
            Err(ReflectError::BadValue)
        }
    }
}
