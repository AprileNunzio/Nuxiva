#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum DeliveryStyle {
    Normal,
    Whisper,
    NightDiscreet,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct AcousticContext {
    pub vocal_energy_rms: f32,
    pub pitch_hz: f32,
    pub is_whisper_detected: bool,
    pub hour_of_day: u8,
    pub is_night_time: bool,
    pub delivery_style: DeliveryStyle,
    pub volume_scale: f32,
}

impl Default for AcousticContext {
    fn default() -> Self {
        Self {
            vocal_energy_rms: 0.15,
            pitch_hz: 140.0,
            is_whisper_detected: false,
            hour_of_day: 14,
            is_night_time: false,
            delivery_style: DeliveryStyle::Normal,
            volume_scale: 1.0,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct AcousticAnalyzer;

impl AcousticAnalyzer {
    pub const WHISPER_RMS_THRESHOLD: f32 = 0.040;
    pub const NIGHT_START_HOUR: u8 = 22;
    pub const NIGHT_END_HOUR: u8 = 7;

    #[must_use]
    pub fn is_night(hour: u8) -> bool {
        !(Self::NIGHT_END_HOUR..Self::NIGHT_START_HOUR).contains(&hour)
    }

    #[must_use]
    pub fn analyze(vocal_energy_rms: f32, pitch_hz: f32, hour_of_day: u8) -> AcousticContext {
        let is_whisper = vocal_energy_rms > 0.001 && vocal_energy_rms < Self::WHISPER_RMS_THRESHOLD;
        let is_night = Self::is_night(hour_of_day);

        let (delivery_style, volume_scale) = if is_whisper {
            (DeliveryStyle::Whisper, 0.35)
        } else if is_night {
            (DeliveryStyle::NightDiscreet, 0.55)
        } else {
            (DeliveryStyle::Normal, 1.0)
        };

        AcousticContext {
            vocal_energy_rms,
            pitch_hz,
            is_whisper_detected: is_whisper,
            hour_of_day,
            is_night_time: is_night,
            delivery_style,
            volume_scale,
        }
    }
}
