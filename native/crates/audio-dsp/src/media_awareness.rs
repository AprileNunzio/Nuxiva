use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum MediaStreamType {
    None,
    Music,
    IptvLive,
    VideoOnDemand,
    SystemNotification,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MediaPlaybackState {
    pub is_active: bool,
    pub source_id: String,
    pub stream_type: MediaStreamType,
    pub volume_normalized: f32,
    pub reference_energy: f32,
}

impl Default for MediaPlaybackState {
    fn default() -> Self {
        Self {
            is_active: false,
            source_id: String::new(),
            stream_type: MediaStreamType::None,
            volume_normalized: 0.0,
            reference_energy: 0.0,
        }
    }
}

impl MediaPlaybackState {
    #[must_use]
    pub fn new(
        is_active: bool,
        source_id: impl Into<String>,
        stream_type: MediaStreamType,
        volume_normalized: f32,
        reference_energy: f32,
    ) -> Self {
        Self {
            is_active,
            source_id: source_id.into(),
            stream_type,
            volume_normalized: volume_normalized.clamp(0.0, 1.0),
            reference_energy: reference_energy.max(0.0),
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct AcousticEchoSuppressor {
    base_attenuation_floor: f32,
}

impl Default for AcousticEchoSuppressor {
    fn default() -> Self {
        Self::new()
    }
}

impl AcousticEchoSuppressor {
    #[must_use]
    pub const fn new() -> Self {
        Self {
            base_attenuation_floor: 0.15,
        }
    }

    #[must_use]
    pub fn compute_suppression_factor(&self, state: &MediaPlaybackState) -> f32 {
        if !state.is_active {
            return 1.0;
        }

        let media_impact = state.volume_normalized * 0.75;
        let factor = 1.0 - media_impact;
        factor.clamp(self.base_attenuation_floor, 1.0)
    }

    #[must_use]
    pub fn compute_adaptive_vad_threshold(
        &self,
        base_threshold: f32,
        state: &MediaPlaybackState,
    ) -> f32 {
        if !state.is_active {
            return base_threshold;
        }

        let penalty = state.volume_normalized * 0.045;
        (base_threshold + penalty).clamp(0.01, 0.5)
    }
}
