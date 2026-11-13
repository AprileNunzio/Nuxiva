use serde::{Deserialize, Serialize};

use crate::error::{PerceptError, PerceptResult};

const DAY_MS: u64 = 86_400_000;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct PerceptSettings {
    pub speaker_ttl_ms: u64,
    pub presence_ttl_ms: u64,
    pub emotion_ttl_ms: u64,
    pub scene_ttl_ms: u64,
    pub audio_ttl_ms: u64,
    pub max_clock_skew_ms: u64,
    pub min_speaker_permille: u16,
    pub max_presence: usize,
    pub max_pending: usize,
}

impl Default for PerceptSettings {
    fn default() -> Self {
        Self {
            speaker_ttl_ms: 30_000,
            presence_ttl_ms: 120_000,
            emotion_ttl_ms: 600_000,
            scene_ttl_ms: 30_000,
            audio_ttl_ms: 15_000,
            max_clock_skew_ms: 5_000,
            min_speaker_permille: 600,
            max_presence: 32,
            max_pending: 256,
        }
    }
}

impl PerceptSettings {
    pub fn validate(&self) -> PerceptResult<()> {
        let windows = [
            self.speaker_ttl_ms,
            self.presence_ttl_ms,
            self.emotion_ttl_ms,
            self.scene_ttl_ms,
            self.audio_ttl_ms,
            self.max_clock_skew_ms,
        ];
        let sane = windows.iter().all(|w| (1..=DAY_MS).contains(w))
            && self.min_speaker_permille <= 1000
            && (1..=256).contains(&self.max_presence)
            && (1..=4096).contains(&self.max_pending);
        if sane {
            Ok(())
        } else {
            Err(PerceptError::Invalid)
        }
    }

    pub fn from_json(raw: &str) -> PerceptResult<Self> {
        let settings: Self = serde_json::from_str(raw).map_err(|_| PerceptError::Invalid)?;
        settings.validate()?;
        Ok(settings)
    }
}
