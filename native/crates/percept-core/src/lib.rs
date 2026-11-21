#![forbid(unsafe_code)]

mod drift;
pub mod embodied;
mod error;
mod fuser;
mod fusion;
mod observation;
mod settings;
mod source;

pub use drift::{CrossModalPerceptFrame, SensoryDriftAlert, SensoryDriftDetector};
pub use embodied::{
    ArmActuatorCapability, DISTRESS_VOCAL_RMS_BPS, EmbodiedMotorCommand, EmbodiedOrgan,
    GAZE_LOCK_CONFIDENCE_BPS, GESTURE_ACTION_CONFIDENCE_BPS, HearingEarSnapshot,
    MAX_MODAL_CHANNELS, SensorimotorFrameOutcome, SpeechVoiceState, VisionEyeSnapshot,
    coordinate_sensorimotor_cycle,
};
pub use error::{PerceptError, PerceptResult};
pub use fuser::Fuser;
pub use fusion::Fusion;
pub use observation::Observation;
pub use settings::PerceptSettings;
pub use source::{PerceptSource, QueueSource};

#[cfg(test)]
#[allow(clippy::expect_used, clippy::arithmetic_side_effects)]
mod tests;
#[cfg(test)]
#[allow(clippy::expect_used, clippy::arithmetic_side_effects)]
mod tests_chaos;
