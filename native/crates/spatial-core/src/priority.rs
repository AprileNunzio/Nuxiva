use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum NotificationPriority {
    #[serde(rename = "P0_CRITICAL")]
    P0Critical = 0,
    #[serde(rename = "P1_HIGH")]
    P1High = 1,
    #[serde(rename = "P2_NORMAL")]
    P2Normal = 2,
    #[serde(rename = "P3_LOW")]
    P3Low = 3,
}

impl NotificationPriority {
    #[must_use]
    pub const fn code(&self) -> &'static str {
        match self {
            Self::P0Critical => "P0",
            Self::P1High => "P1",
            Self::P2Normal => "P2",
            Self::P3Low => "P3",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct NotificationEvent {
    pub id: String,
    pub priority: NotificationPriority,
    pub title_key: String,
    pub message_key: String,
    pub source_module: String,
    pub timestamp_ms: u64,
}

impl NotificationEvent {
    #[must_use]
    pub fn new(
        id: impl Into<String>,
        priority: NotificationPriority,
        title_key: impl Into<String>,
        message_key: impl Into<String>,
        source_module: impl Into<String>,
        timestamp_ms: u64,
    ) -> Self {
        Self {
            id: id.into(),
            priority,
            title_key: title_key.into(),
            message_key: message_key.into(),
            source_module: source_module.into(),
            timestamp_ms,
        }
    }
}
