use serde::{Deserialize, Serialize};

use crate::error::{DuplexError, DuplexResult};
use crate::state::State;

pub const PROTOCOL_VERSION: u32 = 1;
pub const MAX_SETTINGS_BYTES: usize = 16 * 1024;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Settings {
    pub max_audio_bytes: usize,
    pub max_text_bytes: usize,
    pub rate_per_second: u32,
    pub rate_burst: u32,
    pub max_cancel_tokens: usize,
    pub event_cap: usize,
    pub fade_ms: u32,
    pub listening_ms: u64,
    pub thinking_ms: u64,
    pub speaking_ms: u64,
    pub interrupted_ms: u64,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            max_audio_bytes: 4_096,
            max_text_bytes: 4_096,
            rate_per_second: 100,
            rate_burst: 200,
            max_cancel_tokens: 64,
            event_cap: 256,
            fade_ms: 30,
            listening_ms: 30_000,
            thinking_ms: 60_000,
            speaking_ms: 300_000,
            interrupted_ms: 2_000,
        }
    }
}

impl Settings {
    pub fn from_json(text: &str) -> DuplexResult<Self> {
        if text.len() > MAX_SETTINGS_BYTES {
            return Err(DuplexError::TooLarge);
        }
        let settings: Self = serde_json::from_str(text).map_err(|_| DuplexError::Parse)?;
        settings.validate()?;
        Ok(settings)
    }

    pub fn validate(&self) -> DuplexResult<()> {
        let ok = (1..=65_536).contains(&self.max_audio_bytes)
            && (1..=65_536).contains(&self.max_text_bytes)
            && (1..=1_000).contains(&self.rate_per_second)
            && self.rate_burst >= self.rate_per_second
            && self.rate_burst <= 10_000
            && (1..=1_024).contains(&self.max_cancel_tokens)
            && (8..=65_536).contains(&self.event_cap)
            && self.fade_ms <= 30
            && [
                self.listening_ms,
                self.thinking_ms,
                self.speaking_ms,
                self.interrupted_ms,
            ]
            .iter()
            .all(|ms| (100..=3_600_000).contains(ms));
        if ok {
            Ok(())
        } else {
            Err(DuplexError::Settings)
        }
    }

    #[must_use]
    pub const fn limit_ms(&self, state: State) -> Option<u64> {
        match state {
            State::Idle => None,
            State::Listening => Some(self.listening_ms),
            State::Thinking => Some(self.thinking_ms),
            State::Speaking => Some(self.speaking_ms),
            State::Interrupted => Some(self.interrupted_ms),
        }
    }
}
