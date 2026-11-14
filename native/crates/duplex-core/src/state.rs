use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum State {
    Idle,
    Listening,
    Thinking,
    Speaking,
    Interrupted,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Trigger {
    VoiceStart,
    VoiceEnd,
    ReplyStart,
    ReplyEnd,
    Interrupt,
    Resume,
    Reset,
}

impl State {
    #[must_use]
    pub const fn next(self, trigger: Trigger) -> Option<Self> {
        match (self, trigger) {
            (_, Trigger::Reset) | (Self::Speaking, Trigger::ReplyEnd) => Some(Self::Idle),
            (Self::Idle | Self::Thinking, Trigger::VoiceStart)
            | (Self::Interrupted, Trigger::Resume) => Some(Self::Listening),
            (Self::Listening, Trigger::VoiceEnd) => Some(Self::Thinking),
            (Self::Idle | Self::Thinking, Trigger::ReplyStart) => Some(Self::Speaking),
            (Self::Speaking, Trigger::Interrupt) => Some(Self::Interrupted),
            _ => None,
        }
    }

    #[must_use]
    pub const fn on_timeout(self) -> Option<Self> {
        match self {
            Self::Idle => None,
            Self::Interrupted => Some(Self::Listening),
            Self::Listening | Self::Thinking | Self::Speaking => Some(Self::Idle),
        }
    }
}
