use serde::{Deserialize, Serialize};

use crate::error::{ProactivityError, ProactivityResult};
use crate::model::Situation;

pub const MAX_PAYLOAD: usize = 1024 * 1024;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Settings {
    pub cost_idle: u32,
    pub cost_conversation: u32,
    pub cost_sleeping: u32,
    pub cost_guests: u32,
    pub cost_meeting: u32,
    pub hourly_cap: usize,
    pub person_hourly_cap: usize,
    pub dedupe_ms: u64,
    pub mute_ms: u64,
    pub proposal_ttl_ms: u64,
    pub signal_ttl_ms: u64,
    pub quiet_start_min: u32,
    pub quiet_end_min: u32,
    pub pending_cap: usize,
    pub log_cap: usize,
    pub deferred_cap: usize,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            cost_idle: 100,
            cost_conversation: 1_000,
            cost_sleeping: 900,
            cost_guests: 600,
            cost_meeting: 800,
            hourly_cap: 6,
            person_hourly_cap: 4,
            dedupe_ms: 600_000,
            mute_ms: 7 * 86_400_000,
            proposal_ttl_ms: 3_600_000,
            signal_ttl_ms: 6 * 3_600_000,
            quiet_start_min: 1_320,
            quiet_end_min: 420,
            pending_cap: 64,
            log_cap: 512,
            deferred_cap: 256,
        }
    }
}

impl Settings {
    #[must_use]
    pub const fn cost(&self, situation: Situation) -> u32 {
        match situation {
            Situation::Idle => self.cost_idle,
            Situation::Conversation => self.cost_conversation,
            Situation::Sleeping => self.cost_sleeping,
            Situation::Guests => self.cost_guests,
            Situation::Meeting => self.cost_meeting,
        }
    }

    pub fn validate(&self) -> ProactivityResult<()> {
        let costs = [
            self.cost_idle,
            self.cost_conversation,
            self.cost_sleeping,
            self.cost_guests,
            self.cost_meeting,
        ];
        let ok = costs.iter().all(|c| *c <= 1_000)
            && self.cost_conversation == 1_000
            && (1..=1_000).contains(&self.hourly_cap)
            && (1..=self.hourly_cap).contains(&self.person_hourly_cap)
            && (1..=86_400_000).contains(&self.dedupe_ms)
            && (1..=90 * 86_400_000).contains(&self.mute_ms)
            && (1..=86_400_000).contains(&self.proposal_ttl_ms)
            && (1..=7 * 86_400_000).contains(&self.signal_ttl_ms)
            && self.quiet_start_min < 1_440
            && self.quiet_end_min < 1_440
            && (1..=4_096).contains(&self.pending_cap)
            && (1..=65_536).contains(&self.log_cap)
            && (1..=4_096).contains(&self.deferred_cap);
        if ok {
            Ok(())
        } else {
            Err(ProactivityError::Settings)
        }
    }

    pub fn from_json(text: &str) -> ProactivityResult<Self> {
        if text.len() > MAX_PAYLOAD {
            return Err(ProactivityError::TooLarge);
        }
        let settings: Self = serde_json::from_str(text).map_err(|_| ProactivityError::Settings)?;
        settings.validate()?;
        Ok(settings)
    }
}
