use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Policy {
    pub hibernate_after_ms: u64,
    pub sleep_grace_ms: u64,
    pub error_window_ms: u64,
    pub error_limit: usize,
    pub quarantine_ms: u64,
    pub cost_smoothing: f32,
    pub max_widgets: usize,
}

impl Default for Policy {
    fn default() -> Self {
        Self {
            hibernate_after_ms: 120_000,
            sleep_grace_ms: 60_000,
            error_window_ms: 60_000,
            error_limit: 3,
            quarantine_ms: 300_000,
            cost_smoothing: 0.3,
            max_widgets: 512,
        }
    }
}
