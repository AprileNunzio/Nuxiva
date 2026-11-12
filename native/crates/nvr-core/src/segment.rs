use serde::{Deserialize, Serialize};

use crate::error::{NvrError, NvrResult};

pub const MAX_ID: usize = 64;
pub const MAX_DURATION_MS: u32 = 3_600_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Tier {
    Continuous,
    Event,
    Pinned,
}

impl Tier {
    #[must_use]
    pub fn parse(text: &str) -> Option<Self> {
        match text {
            "continuous" => Some(Self::Continuous),
            "event" => Some(Self::Event),
            "pinned" => Some(Self::Pinned),
            _ => None,
        }
    }

    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Continuous => "continuous",
            Self::Event => "event",
            Self::Pinned => "pinned",
        }
    }
}

#[must_use]
pub fn valid_id(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= MAX_ID
        && value
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'_')
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Segment {
    pub id: String,
    pub camera: String,
    pub start_ms: u64,
    pub duration_ms: u32,
    pub bytes: u64,
    pub tier: Tier,
    pub audio: bool,
    pub video: bool,
}

impl Segment {
    #[must_use]
    pub fn end_ms(&self) -> u64 {
        self.start_ms.saturating_add(u64::from(self.duration_ms))
    }

    #[must_use]
    pub fn overlaps(&self, from_ms: u64, to_ms: u64) -> bool {
        self.start_ms < to_ms && self.end_ms() > from_ms
    }

    pub fn validate(&self) -> NvrResult<()> {
        if !valid_id(&self.id) || !valid_id(&self.camera) {
            return Err(NvrError::InvalidId);
        }
        if self.duration_ms == 0 || self.duration_ms > MAX_DURATION_MS {
            return Err(NvrError::InvalidSegment);
        }
        Ok(())
    }
}
