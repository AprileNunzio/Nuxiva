use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum RetentionTier {
    Continuous,
    EventClip,
    Pinned,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RetentionPolicy {
    pub continuous_seconds: u64,
    pub event_seconds: u64,
}

impl Default for RetentionPolicy {
    fn default() -> Self {
        Self {
            continuous_seconds: 7200,
            event_seconds: 604_800,
        }
    }
}

impl RetentionPolicy {
    #[must_use]
    pub const fn new(continuous_seconds: u64, event_seconds: u64) -> Self {
        Self {
            continuous_seconds,
            event_seconds,
        }
    }

    #[must_use]
    pub fn is_expired(&self, tier: RetentionTier, recorded_at: u64, now: u64) -> bool {
        match tier {
            RetentionTier::Pinned => false,
            RetentionTier::Continuous => now
                .checked_sub(recorded_at)
                .is_some_and(|diff| diff > self.continuous_seconds),
            RetentionTier::EventClip => now
                .checked_sub(recorded_at)
                .is_some_and(|diff| diff > self.event_seconds),
        }
    }
}
