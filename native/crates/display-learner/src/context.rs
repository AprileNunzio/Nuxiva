use serde::{Deserialize, Serialize};

pub const BANDS: usize = 6;
pub const FEATURES: usize = 20;
pub const ACTIVE: usize = 6;
pub const BIAS: usize = 19;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Activity {
    Conversation,
    Project,
    Media,
    #[default]
    Ambient,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ScreenRole {
    #[default]
    Main,
    Side,
    Kitchen,
    Other,
}

impl ScreenRole {
    #[must_use]
    pub const fn index(self) -> usize {
        match self {
            Self::Main => 0,
            Self::Side => 1,
            Self::Kitchen => 2,
            Self::Other => 3,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(default)]
pub struct ContextVector {
    pub band: u8,
    pub weekend: bool,
    pub activity: Activity,
    pub crowd: u8,
    pub role: ScreenRole,
}

impl ContextVector {
    #[must_use]
    pub fn features(&self) -> [usize; ACTIVE] {
        let band = usize::from(self.band).min(BANDS.saturating_sub(1));
        let day = if self.weekend { 7 } else { 6 };
        let activity = match self.activity {
            Activity::Conversation => 8,
            Activity::Project => 9,
            Activity::Media => 10,
            Activity::Ambient => 11,
        };
        let crowd = match self.crowd {
            0 => 12,
            1 => 13,
            _ => 14,
        };
        let role = match self.role {
            ScreenRole::Main => 15,
            ScreenRole::Side => 16,
            ScreenRole::Kitchen => 17,
            ScreenRole::Other => 18,
        };
        [band, day, activity, crowd, role, BIAS]
    }
}
