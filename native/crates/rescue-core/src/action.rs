use serde::Serialize;

use crate::fusion::Assessment;
use crate::signal::Hazard;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Stage {
    Calm,
    Watching,
    CheckIn,
    Alerting,
    Acknowledged,
    Emergency,
    Cooldown,
}

impl Stage {
    #[must_use]
    pub const fn active(self) -> bool {
        matches!(
            self,
            Self::CheckIn | Self::Alerting | Self::Acknowledged | Self::Emergency
        )
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Tone {
    Spoken,
    Discreet,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum Action {
    AskPerson {
        hazard: Hazard,
        tone: Tone,
    },
    AlertFamily {
        hazard: Hazard,
        tier: u8,
        tone: Tone,
    },
    AlertEmergencyContacts {
        hazard: Hazard,
        round: u8,
    },
    RemindEmergencyNumber {
        hazard: Hazard,
    },
    HomeAlarm {
        hazard: Hazard,
    },
    Acknowledged {
        tier: u8,
    },
    StandDown {
        hazard: Hazard,
        notified_tiers: u8,
        emergency: bool,
    },
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Entry {
    pub at: f64,
    pub stage: Stage,
    pub action: Option<Action>,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Step {
    pub at: f64,
    pub stage: Stage,
    pub hazard: Option<Hazard>,
    pub incident: u64,
    pub deadline: Option<f64>,
    pub actions: Vec<Action>,
    pub assessment: Assessment,
}
