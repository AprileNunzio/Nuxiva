use serde::{Deserialize, Serialize};

use crate::error::{InitiativeError, InitiativeResult};

pub const MAX_PAYLOAD: usize = 1024 * 1024;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Situation {
    Idle,
    Conversation,
    Sleeping,
    Guests,
    Meeting,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Settings {
    pub cost_idle: u32,
    pub cost_conversation: u32,
    pub cost_sleeping: u32,
    pub cost_guests: u32,
    pub cost_meeting: u32,
    pub hourly_cap: usize,
    pub dedupe_ms: u64,
    pub refusal_ms: u64,
    pub proposal_ttl_ms: u64,
    pub pending_cap: usize,
    pub diary_cap: usize,
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
            dedupe_ms: 600_000,
            refusal_ms: 86_400_000,
            proposal_ttl_ms: 3_600_000,
            pending_cap: 64,
            diary_cap: 256,
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

    pub fn validate(&self) -> InitiativeResult<()> {
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
            && (1..=86_400_000).contains(&self.dedupe_ms)
            && (1..=30 * 86_400_000).contains(&self.refusal_ms)
            && (1..=86_400_000).contains(&self.proposal_ttl_ms)
            && (1..=4_096).contains(&self.pending_cap)
            && (1..=65_536).contains(&self.diary_cap);
        if ok {
            Ok(())
        } else {
            Err(InitiativeError::Settings)
        }
    }

    pub fn from_json(text: &str) -> InitiativeResult<Self> {
        if text.len() > MAX_PAYLOAD {
            return Err(InitiativeError::TooLarge);
        }
        let settings: Self = serde_json::from_str(text).map_err(|_| InitiativeError::Settings)?;
        settings.validate()?;
        Ok(settings)
    }
}
