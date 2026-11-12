use serde::{Deserialize, Serialize};

pub const MAX_SOURCE: usize = 96;
pub const MAX_EVIDENCE: usize = 512;
pub const MAX_FUTURE_S: f64 = 5.0;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Kind {
    HelpWords,
    Scream,
    Fall,
    Immobility,
    Vitals,
    NoResponse,
    Smoke,
    Fire,
    Intrusion,
    Violence,
    AllClear,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Hazard {
    Medical,
    Fire,
    Intrusion,
    Violence,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Modality {
    Audio,
    Vision,
    Body,
    Environment,
    Interaction,
}

impl Kind {
    pub const ALL: [Self; 11] = [
        Self::HelpWords,
        Self::Scream,
        Self::Fall,
        Self::Immobility,
        Self::Vitals,
        Self::NoResponse,
        Self::Smoke,
        Self::Fire,
        Self::Intrusion,
        Self::Violence,
        Self::AllClear,
    ];

    #[must_use]
    pub const fn hazards(self) -> &'static [Hazard] {
        match self {
            Self::HelpWords | Self::Scream | Self::AllClear => &[Hazard::Medical, Hazard::Violence],
            Self::Fall | Self::Immobility | Self::Vitals | Self::NoResponse => &[Hazard::Medical],
            Self::Smoke | Self::Fire => &[Hazard::Fire],
            Self::Intrusion => &[Hazard::Intrusion],
            Self::Violence => &[Hazard::Violence],
        }
    }

    #[must_use]
    pub const fn modality(self) -> Modality {
        match self {
            Self::HelpWords | Self::Scream | Self::Violence => Modality::Audio,
            Self::Fall | Self::Immobility | Self::Intrusion => Modality::Vision,
            Self::Vitals => Modality::Body,
            Self::Smoke | Self::Fire => Modality::Environment,
            Self::NoResponse | Self::AllClear => Modality::Interaction,
        }
    }

    #[must_use]
    pub const fn reliability(self) -> f64 {
        match self {
            Self::HelpWords => 0.85,
            Self::Scream | Self::Immobility => 0.6,
            Self::Fall => 0.75,
            Self::Vitals | Self::NoResponse => 0.5,
            Self::Smoke | Self::Fire | Self::AllClear => 0.9,
            Self::Intrusion => 0.7,
            Self::Violence => 0.4,
        }
    }

    #[must_use]
    pub const fn half_life(self) -> f64 {
        match self {
            Self::HelpWords | Self::Immobility | Self::Vitals | Self::Violence => 120.0,
            Self::Scream => 60.0,
            Self::Fall => 600.0,
            Self::NoResponse | Self::Smoke | Self::Fire | Self::Intrusion => 300.0,
            Self::AllClear => 180.0,
        }
    }

    #[must_use]
    pub const fn reassuring(self) -> bool {
        matches!(self, Self::AllClear)
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Evidence {
    pub kind: Kind,
    pub probability: f64,
    pub confidence: f64,
    pub source: String,
    #[serde(default)]
    pub room: Option<String>,
    pub at: f64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EvidenceError {
    Probability,
    Confidence,
    Source,
    Room,
    Time,
}

impl EvidenceError {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Probability => "rescue.evidence.probability",
            Self::Confidence => "rescue.evidence.confidence",
            Self::Source => "rescue.evidence.source",
            Self::Room => "rescue.evidence.room",
            Self::Time => "rescue.evidence.time",
        }
    }
}

fn label_ok(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= MAX_SOURCE
        && value
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '_' | '-' | '.' | ':' | '/'))
}

impl Evidence {
    pub fn validate(&self, now: f64) -> Result<(), EvidenceError> {
        if !self.probability.is_finite() || !(0.0..=1.0).contains(&self.probability) {
            return Err(EvidenceError::Probability);
        }
        if !self.confidence.is_finite() || !(0.0..=1.0).contains(&self.confidence) {
            return Err(EvidenceError::Confidence);
        }
        if !label_ok(&self.source) {
            return Err(EvidenceError::Source);
        }
        if self.room.as_deref().is_some_and(|r| !label_ok(r)) {
            return Err(EvidenceError::Room);
        }
        if !self.at.is_finite() || self.at < 0.0 || !now.is_finite() || self.at > now + MAX_FUTURE_S
        {
            return Err(EvidenceError::Time);
        }
        Ok(())
    }

    #[must_use]
    pub fn expired(&self, now: f64) -> bool {
        now - self.at > self.kind.half_life() * 4.0
    }
}
