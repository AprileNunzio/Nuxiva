use nuxiva_swarm_core::Ident;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CrossModalPerceptFrame {
    pub hw_timestamp_ns: u64,
    pub jitter_offset_ns: i64,
    pub audio_level_rms: f32,
    pub vision_motion_score: f32,
    pub presence_detected: bool,
    pub active_speaker: Option<Ident>,
    pub vitals_cpu_percent: f32,
    pub vitals_ram_available_mb: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum SensoryDriftAlert {
    ExcessiveJitter {
        offset_ns: i64,
        limit_ns: i64,
    },
    SensorFrozenOrLoss {
        sensor: &'static str,
    },
    SignalSaturated {
        sensor: &'static str,
        value_rms: u16,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SensoryDriftDetector {
    max_jitter_tolerance_ns: i64,
    consecutive_silent_frames: usize,
    max_silent_frames_before_alert: usize,
}

impl SensoryDriftDetector {
    #[must_use]
    pub const fn new(max_jitter_tolerance_ns: i64, max_silent_frames_before_alert: usize) -> Self {
        Self {
            max_jitter_tolerance_ns,
            consecutive_silent_frames: 0,
            max_silent_frames_before_alert,
        }
    }

    pub fn record_frame(&mut self, frame: &CrossModalPerceptFrame) -> Option<SensoryDriftAlert> {
        if frame.jitter_offset_ns.abs() > self.max_jitter_tolerance_ns {
            return Some(SensoryDriftAlert::ExcessiveJitter {
                offset_ns: frame.jitter_offset_ns,
                limit_ns: self.max_jitter_tolerance_ns,
            });
        }

        if frame.audio_level_rms >= 0.99 {
            return Some(SensoryDriftAlert::SignalSaturated {
                sensor: "microphone",
                value_rms: 1000,
            });
        }

        if frame.audio_level_rms <= 0.0001 && frame.vision_motion_score <= 0.0001 {
            self.consecutive_silent_frames = self.consecutive_silent_frames.saturating_add(1);
            if self.consecutive_silent_frames >= self.max_silent_frames_before_alert {
                return Some(SensoryDriftAlert::SensorFrozenOrLoss {
                    sensor: "multimodal_av",
                });
            }
        } else {
            self.consecutive_silent_frames = 0;
        }

        None
    }
}
