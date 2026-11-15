#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct GazeInput {
    pub gaze_score: f32,
    pub face_detected: bool,
    pub distance_meters: f32,
    pub voice_proximity: f32,
}

impl Default for GazeInput {
    fn default() -> Self {
        Self {
            gaze_score: 0.0,
            face_detected: false,
            distance_meters: 3.0,
            voice_proximity: 0.1,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GazeGateDecision {
    pub is_activated: bool,
    pub requires_wakeword: bool,
    pub engagement_score: f32,
    pub reason: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct GazeAcousticGate;

impl GazeAcousticGate {
    pub const GAZE_ACTIVATION_THRESHOLD: f32 = 0.65;
    pub const MAX_NATURAL_DISTANCE_M: f32 = 2.5;
    pub const MIN_VOICE_PROXIMITY: f32 = 0.12;

    #[must_use]
    pub fn evaluate(input: GazeInput) -> GazeGateDecision {
        if !input.face_detected {
            return GazeGateDecision {
                is_activated: false,
                requires_wakeword: true,
                engagement_score: 0.0,
                reason: "no_face_detected".to_owned(),
            };
        }

        let dist_factor = (Self::MAX_NATURAL_DISTANCE_M
            - input
                .distance_meters
                .clamp(0.0, Self::MAX_NATURAL_DISTANCE_M))
            / Self::MAX_NATURAL_DISTANCE_M;

        let engagement = (0.50 * input.gaze_score.clamp(0.0, 1.0))
            + (0.30 * dist_factor)
            + (0.20 * input.voice_proximity.clamp(0.0, 1.0));

        let is_direct_gaze = input.gaze_score >= Self::GAZE_ACTIVATION_THRESHOLD
            && input.distance_meters <= Self::MAX_NATURAL_DISTANCE_M
            && input.voice_proximity >= Self::MIN_VOICE_PROXIMITY;

        if is_direct_gaze {
            GazeGateDecision {
                is_activated: true,
                requires_wakeword: false,
                engagement_score: engagement,
                reason: "natural_gaze_contact".to_owned(),
            }
        } else {
            GazeGateDecision {
                is_activated: false,
                requires_wakeword: true,
                engagement_score: engagement,
                reason: "gaze_indirect_requires_wake".to_owned(),
            }
        }
    }
}
