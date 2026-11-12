use serde::{Deserialize, Serialize};

use crate::error::MemoryError;
use crate::look::{Look, Vehicle};

pub const GAIT_LEN: usize = 16;
pub const MAX_EVIDENCE: usize = 8;
pub const MAX_SPAN_MS: u64 = 6 * 3_600_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Class {
    Person,
    Vehicle,
    Parcel,
    Animal,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(tag = "type", content = "id", rename_all = "snake_case")]
pub enum Who {
    Person(String),
    Guest(u16),
    Unknown,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Audience {
    Household,
    Guest,
    Passerby,
    Object,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EvidenceKind {
    Frame,
    Clip,
    Audio,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Evidence {
    pub kind: EvidenceKind,
    pub id: String,
    pub at_ms: u64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Sighting {
    pub id: String,
    pub start_ms: u64,
    pub end_ms: u64,
    pub camera: String,
    #[serde(default)]
    pub zone: Option<String>,
    pub class: Class,
    pub who: Who,
    #[serde(default)]
    pub look: Look,
    #[serde(default)]
    pub vehicle: Option<Vehicle>,
    #[serde(default)]
    pub gait: Vec<f32>,
    #[serde(default)]
    pub evidence: Vec<Evidence>,
    pub confidence: f32,
    #[serde(default)]
    pub pinned: bool,
}

pub(crate) fn token(value: &str, max: usize) -> bool {
    !value.is_empty()
        && value.len() <= max
        && value.bytes().all(|b| {
            b.is_ascii_lowercase() || b.is_ascii_digit() || matches!(b, b'_' | b'.' | b'-')
        })
}

pub(crate) fn hex(value: &str, min: usize, max: usize) -> bool {
    (min..=max).contains(&value.len()) && value.bytes().all(|b| b.is_ascii_hexdigit())
}

impl Who {
    #[must_use]
    pub fn key(&self) -> String {
        match self {
            Self::Person(p) => format!("person:{p}"),
            Self::Guest(n) => format!("guest:{n}"),
            Self::Unknown => "unknown".to_owned(),
        }
    }

    #[must_use]
    pub fn valid(&self) -> bool {
        match self {
            Self::Person(p) => hex(p, 32, 64),
            Self::Guest(n) => *n > 0,
            Self::Unknown => true,
        }
    }
}

impl Sighting {
    #[must_use]
    pub fn audience(&self) -> Audience {
        match (&self.who, self.class) {
            (Who::Person(_), _) => Audience::Household,
            (Who::Guest(_), _) => Audience::Guest,
            (Who::Unknown, Class::Person) => Audience::Passerby,
            (Who::Unknown, _) => Audience::Object,
        }
    }

    pub fn validate(&self) -> Result<(), MemoryError> {
        if !hex(&self.id, 16, 32) {
            return Err(MemoryError::InvalidSighting("id"));
        }
        if self.end_ms < self.start_ms || self.end_ms.saturating_sub(self.start_ms) > MAX_SPAN_MS {
            return Err(MemoryError::InvalidSighting("time"));
        }
        if !token(&self.camera, 64) || self.zone.as_deref().is_some_and(|z| !token(z, 64)) {
            return Err(MemoryError::InvalidSighting("place"));
        }
        if !self.who.valid() {
            return Err(MemoryError::InvalidSighting("who"));
        }
        if !self.look.valid() {
            return Err(MemoryError::InvalidSighting("look"));
        }
        if self.vehicle.is_some() != (self.class == Class::Vehicle) {
            return Err(MemoryError::InvalidSighting("vehicle"));
        }
        if !(self.gait.is_empty() || self.gait.len() == GAIT_LEN)
            || !self.gait.iter().all(|v| v.is_finite() && v.abs() <= 1e3)
        {
            return Err(MemoryError::InvalidSighting("gait"));
        }
        if self.evidence.len() > MAX_EVIDENCE || !self.evidence.iter().all(|e| hex(&e.id, 16, 32)) {
            return Err(MemoryError::InvalidSighting("evidence"));
        }
        if !(0.0..=1.0).contains(&self.confidence) {
            return Err(MemoryError::InvalidSighting("confidence"));
        }
        Ok(())
    }
}
