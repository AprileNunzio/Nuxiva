use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::error::SentinelError;
use crate::kind::Kind;

pub const MAX_PARAMS: usize = 8;
pub const MAX_VALUE: usize = 120;
pub const MAX_LINKS: usize = 2;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Sensitivity {
    Public,
    #[default]
    Household,
    Personal,
    Sensitive,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "type", content = "id", rename_all = "snake_case")]
pub enum Subject {
    Person(String),
    Guest(u16),
    Nuxiva,
    Device(String),
    Automation(String),
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Narrative {
    pub key: String,
    #[serde(default)]
    pub params: BTreeMap<String, String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Event {
    pub id: String,
    pub at_ms: u64,
    pub kind: Kind,
    pub subject: Subject,
    #[serde(default)]
    pub place: Option<String>,
    pub narrative: Narrative,
    #[serde(default)]
    pub sensitivity: Sensitivity,
    pub source: String,
    #[serde(default)]
    pub links: Vec<String>,
}

fn token(value: &str, max: usize) -> bool {
    !value.is_empty()
        && value.len() <= max
        && value.bytes().all(|b| {
            b.is_ascii_lowercase() || b.is_ascii_digit() || matches!(b, b'_' | b'.' | b'-' | b':')
        })
}

fn text(value: &str) -> bool {
    value.chars().count() <= MAX_VALUE && !value.chars().any(char::is_control)
}

fn hex(value: &str, min: usize, max: usize) -> bool {
    (min..=max).contains(&value.len()) && value.bytes().all(|b| b.is_ascii_hexdigit())
}

impl Subject {
    #[must_use]
    pub fn key(&self) -> String {
        match self {
            Self::Person(p) => format!("person:{p}"),
            Self::Guest(n) => format!("guest:{n}"),
            Self::Nuxiva => "nuxiva".to_owned(),
            Self::Device(d) => format!("device:{d}"),
            Self::Automation(a) => format!("automation:{a}"),
        }
    }

    fn valid(&self) -> bool {
        match self {
            Self::Person(p) => hex(p, 32, 64),
            Self::Guest(n) => *n > 0,
            Self::Nuxiva => true,
            Self::Device(id) | Self::Automation(id) => token(id, 96),
        }
    }
}

impl Event {
    pub fn validate(&self) -> Result<(), SentinelError> {
        if !hex(&self.id, 16, 32) {
            return Err(SentinelError::InvalidEvent("id"));
        }
        if !self.subject.valid() {
            return Err(SentinelError::InvalidEvent("subject"));
        }
        if !self.narrative.key.starts_with("sentinel.") || !token(&self.narrative.key, 96) {
            return Err(SentinelError::InvalidEvent("narrative"));
        }
        if self.narrative.params.len() > MAX_PARAMS
            || !self
                .narrative
                .params
                .iter()
                .all(|(k, v)| token(k, 32) && text(v))
        {
            return Err(SentinelError::InvalidEvent("params"));
        }
        if self.place.as_deref().is_some_and(|p| !token(p, 64)) {
            return Err(SentinelError::InvalidEvent("place"));
        }
        if !token(&self.source, 48) {
            return Err(SentinelError::InvalidEvent("source"));
        }
        if self.links.len() > MAX_LINKS || !self.links.iter().all(|l| hex(l, 16, 32)) {
            return Err(SentinelError::InvalidEvent("links"));
        }
        Ok(())
    }
}
