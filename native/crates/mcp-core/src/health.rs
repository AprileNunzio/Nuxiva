use crate::error::McpError;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Health {
    Disconnected,
    Connecting,
    Ready,
    Degraded,
    Quarantined,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ServerStatus {
    pub health: Health,
    pub tools: usize,
    pub attempts: u32,
    pub last_error: Option<McpError>,
}

impl Health {
    #[must_use]
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Disconnected => "disconnected",
            Self::Connecting => "connecting",
            Self::Ready => "ready",
            Self::Degraded => "degraded",
            Self::Quarantined => "quarantined",
        }
    }
}

impl ServerStatus {
    #[must_use]
    pub fn new() -> Self {
        Self {
            health: Health::Disconnected,
            tools: 0,
            attempts: 0,
            last_error: None,
        }
    }
}

impl Default for ServerStatus {
    fn default() -> Self {
        Self::new()
    }
}
