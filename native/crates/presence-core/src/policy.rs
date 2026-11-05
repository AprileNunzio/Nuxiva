use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields, default)]
pub struct Policy {
    pub stable_ms: u64,
    pub away_ms: u64,
    pub voice_hold_ms: u64,
    pub agree_ms: u64,
    pub skew_ms: u64,
    pub face_min: f32,
    pub voice_min: f32,
    pub require_liveness: bool,
}

impl Default for Policy {
    fn default() -> Self {
        Self {
            stable_ms: 1_200,
            away_ms: 10_000,
            voice_hold_ms: 30_000,
            agree_ms: 10_000,
            skew_ms: 2_000,
            face_min: 0.5,
            voice_min: 0.5,
            require_liveness: true,
        }
    }
}
