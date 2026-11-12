use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum Kind {
    #[serde(rename = "presence.arrived")]
    PresenceArrived,
    #[serde(rename = "presence.left")]
    PresenceLeft,
    #[serde(rename = "presence.near_screen")]
    PresenceNearScreen,
    #[serde(rename = "appearance.noted")]
    AppearanceNoted,
    #[serde(rename = "guest.arrived")]
    GuestArrived,
    #[serde(rename = "guest.left")]
    GuestLeft,
    #[serde(rename = "guest.appearance")]
    GuestAppearance,
    #[serde(rename = "voice.recognized")]
    VoiceRecognized,
    #[serde(rename = "voice.unknown")]
    VoiceUnknown,
    #[serde(rename = "access.allowed")]
    AccessAllowed,
    #[serde(rename = "access.denied")]
    AccessDenied,
    #[serde(rename = "access.confirm_requested")]
    AccessConfirmRequested,
    #[serde(rename = "automation.started")]
    AutomationStarted,
    #[serde(rename = "automation.finished")]
    AutomationFinished,
    #[serde(rename = "automation.failed")]
    AutomationFailed,
    #[serde(rename = "self.idle_study")]
    SelfIdleStudy,
    #[serde(rename = "self.learned")]
    SelfLearned,
    #[serde(rename = "self.maintenance")]
    SelfMaintenance,
    #[serde(rename = "self.chat_request")]
    ChatRequest,
    #[serde(rename = "self.mcp_request")]
    McpRequest,
    #[serde(rename = "display.scene_changed")]
    DisplaySceneChanged,
    #[serde(rename = "display.privacy_shutter")]
    DisplayPrivacyShutter,
    #[serde(rename = "system.alert")]
    SystemAlert,
    #[serde(rename = "system.recovered")]
    SystemRecovered,
    #[serde(rename = "sentinel.read")]
    SentinelRead,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Group {
    Presence,
    Appearance,
    Guests,
    GuestAppearance,
    Voice,
    Access,
    Denied,
    Automations,
    Nuxiva,
    Display,
    System,
    Audit,
}

pub const ALL: [Kind; 25] = [
    Kind::PresenceArrived,
    Kind::PresenceLeft,
    Kind::PresenceNearScreen,
    Kind::AppearanceNoted,
    Kind::GuestArrived,
    Kind::GuestLeft,
    Kind::GuestAppearance,
    Kind::VoiceRecognized,
    Kind::VoiceUnknown,
    Kind::AccessAllowed,
    Kind::AccessDenied,
    Kind::AccessConfirmRequested,
    Kind::AutomationStarted,
    Kind::AutomationFinished,
    Kind::AutomationFailed,
    Kind::SelfIdleStudy,
    Kind::SelfLearned,
    Kind::SelfMaintenance,
    Kind::ChatRequest,
    Kind::McpRequest,
    Kind::DisplaySceneChanged,
    Kind::DisplayPrivacyShutter,
    Kind::SystemAlert,
    Kind::SystemRecovered,
    Kind::SentinelRead,
];

impl Kind {
    #[must_use]
    pub const fn group(self) -> Group {
        match self {
            Self::PresenceArrived | Self::PresenceLeft | Self::PresenceNearScreen => {
                Group::Presence
            }
            Self::AppearanceNoted => Group::Appearance,
            Self::GuestArrived | Self::GuestLeft => Group::Guests,
            Self::GuestAppearance => Group::GuestAppearance,
            Self::VoiceRecognized | Self::VoiceUnknown => Group::Voice,
            Self::AccessAllowed | Self::AccessConfirmRequested => Group::Access,
            Self::AccessDenied => Group::Denied,
            Self::AutomationStarted | Self::AutomationFinished | Self::AutomationFailed => {
                Group::Automations
            }
            Self::SelfIdleStudy
            | Self::SelfLearned
            | Self::SelfMaintenance
            | Self::ChatRequest
            | Self::McpRequest => Group::Nuxiva,
            Self::DisplaySceneChanged | Self::DisplayPrivacyShutter => Group::Display,
            Self::SystemAlert | Self::SystemRecovered => Group::System,
            Self::SentinelRead => Group::Audit,
        }
    }

    #[must_use]
    pub fn name(self) -> String {
        serde_json::to_value(self)
            .ok()
            .and_then(|v| v.as_str().map(str::to_owned))
            .unwrap_or_default()
    }
}
