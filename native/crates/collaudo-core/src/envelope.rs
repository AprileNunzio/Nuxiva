use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::error::CollaudoError;

pub const SCHEMA: u8 = 1;
pub const MAX_FIELDS: usize = 24;
pub const MAX_KEY: usize = 32;
pub const MAX_TOKEN: usize = 64;
pub const MAX_TEXT: usize = 160;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Domain {
    Sentinel,
    Ear,
    Vision,
    Supervisor,
    Worker,
    Mcp,
    Error,
    Resource,
    Probe,
    System,
}

impl Domain {
    #[must_use]
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Sentinel => "sentinel",
            Self::Ear => "ear",
            Self::Vision => "vision",
            Self::Supervisor => "supervisor",
            Self::Worker => "worker",
            Self::Mcp => "mcp",
            Self::Error => "error",
            Self::Resource => "resource",
            Self::Probe => "probe",
            Self::System => "system",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Level {
    Trace,
    Debug,
    Info,
    Warn,
    Error,
}

impl Level {
    #[must_use]
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Trace => "trace",
            Self::Debug => "debug",
            Self::Info => "info",
            Self::Warn => "warn",
            Self::Error => "error",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum Scalar {
    Bool(bool),
    Int(i64),
    Float(f64),
    Text(String),
}

impl Scalar {
    #[must_use]
    #[allow(clippy::cast_precision_loss)]
    pub fn as_f64(&self) -> Option<f64> {
        match self {
            Self::Int(v) => Some(*v as f64),
            Self::Float(v) => Some(*v),
            _ => None,
        }
    }

    #[must_use]
    pub fn matches(&self, other: &Scalar) -> bool {
        match (self, other) {
            (Self::Text(a), Self::Text(b)) => a == b,
            (Self::Bool(a), Self::Bool(b)) => a == b,
            _ => match (self.as_f64(), other.as_f64()) {
                (Some(a), Some(b)) => (a - b).abs() < f64::EPSILON,
                _ => false,
            },
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RawEvent {
    pub domain: Domain,
    pub level: Level,
    pub kind: String,
    #[serde(default)]
    pub corr: Option<String>,
    pub src: String,
    #[serde(default)]
    pub fields: BTreeMap<String, Scalar>,
    #[serde(default)]
    pub at_ms: Option<u64>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Envelope {
    pub v: u8,
    pub seq: u64,
    pub id: String,
    pub at_ms: u64,
    pub domain: Domain,
    pub level: Level,
    pub kind: String,
    #[serde(default)]
    pub corr: Option<String>,
    pub src: String,
    #[serde(default)]
    pub fields: BTreeMap<String, Scalar>,
}

#[must_use]
pub fn is_token(value: &str, max: usize) -> bool {
    !value.is_empty()
        && value.len() <= max
        && value.bytes().all(|b| {
            b.is_ascii_lowercase() || b.is_ascii_digit() || matches!(b, b'_' | b'.' | b'-' | b':')
        })
}

#[must_use]
pub fn is_hex(value: &str, min: usize, max: usize) -> bool {
    (min..=max).contains(&value.len())
        && value
            .bytes()
            .all(|b| matches!(b, b'0'..=b'9' | b'a'..=b'f'))
}

fn clean_text(value: &str) -> bool {
    value.chars().count() <= MAX_TEXT && !value.chars().any(char::is_control)
}

impl Envelope {
    pub fn validate(&self) -> Result<(), CollaudoError> {
        if self.v != SCHEMA {
            return Err(CollaudoError::Invalid("schema"));
        }
        if !is_hex(&self.id, 16, 32) {
            return Err(CollaudoError::Invalid("id"));
        }
        if !is_token(&self.kind, MAX_TOKEN) {
            return Err(CollaudoError::Invalid("kind"));
        }
        if !is_token(&self.src, 48) {
            return Err(CollaudoError::Invalid("src"));
        }
        if self.corr.as_deref().is_some_and(|c| !is_hex(c, 8, 32)) {
            return Err(CollaudoError::Invalid("corr"));
        }
        if self.fields.len() > MAX_FIELDS {
            return Err(CollaudoError::Invalid("fields"));
        }
        for (key, value) in &self.fields {
            if !is_token(key, MAX_KEY) {
                return Err(CollaudoError::Invalid("field_key"));
            }
            let ok = match value {
                Scalar::Float(v) => v.is_finite(),
                Scalar::Text(t) => clean_text(t),
                _ => true,
            };
            if !ok {
                return Err(CollaudoError::Invalid("field_value"));
            }
        }
        Ok(())
    }
}
