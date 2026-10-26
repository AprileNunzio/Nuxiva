use crate::media_awareness::{AcousticEchoSuppressor, MediaPlaybackState};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum VadDecision {
    Silence,
    Speech,
    MusicOrBackground,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct VadResult {
    pub decision: VadDecision,
    pub speech_confidence: f32,
    pub energy_rms: f32,
    pub is_speech: bool,
    pub reason_code: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct SpectralEntropyVad {
    base_energy_threshold: f32,
    min_speech_frames: usize,
    speech_frame_count: usize,
    hangover_frames: usize,
    hangover_remaining: usize,
    suppressor: AcousticEchoSuppressor,
}

impl Default for SpectralEntropyVad {
    fn default() -> Self {
        Self::new(0.018, 2, 4)
    }
}

impl SpectralEntropyVad {
    #[must_use]
    pub const fn new(
        base_energy_threshold: f32,
        min_speech_frames: usize,
        hangover_frames: usize,
    ) -> Self {
        Self {
            base_energy_threshold,
            min_speech_frames,
            speech_frame_count: 0,
            hangover_frames,
            hangover_remaining: 0,
            suppressor: AcousticEchoSuppressor::new(),
        }
    }

    #[must_use]
    pub fn compute_rms(frame: &[i16]) -> f32 {
        if frame.is_empty() {
            return 0.0;
        }

        let mut sum_sq = 0.0_f32;
        for &sample in frame {
            let norm = f32::from(sample) / 32_768.0;
            sum_sq += norm * norm;
        }

        #[allow(clippy::cast_precision_loss)]
        let len_f = frame.len() as f32;
        (sum_sq / len_f).sqrt()
    }

    #[must_use]
    pub fn compute_zero_crossing_rate(frame: &[i16]) -> f32 {
        if frame.len() < 2 {
            return 0.0;
        }

        let mut crossings: usize = 0;
        let mut prev_sign = frame.first().copied().unwrap_or(0) >= 0;

        for &sample in frame.iter().skip(1) {
            let curr_sign = sample >= 0;
            if curr_sign != prev_sign {
                crossings = crossings.saturating_add(1);
                prev_sign = curr_sign;
            }
        }

        #[allow(clippy::cast_precision_loss)]
        let total = (frame.len().saturating_sub(1)) as f32;
        #[allow(clippy::cast_precision_loss)]
        let cr_f = crossings as f32;
        cr_f / total.max(1.0)
    }

    #[must_use]
    pub fn compute_spectral_entropy(frame: &[i16]) -> f32 {
        if frame.len() < 4 {
            return 0.0;
        }

        let mut band_low = 0.0_f32;
        let mut band_mid = 0.0_f32;
        let mut band_high = 0.0_f32;

        let mut step: usize = 0;
        for &sample in frame {
            let s = (f32::from(sample) / 32_768.0).abs();
            let idx = step % 3;
            if idx == 0 {
                band_low += s;
            } else if idx == 1 {
                band_mid += s;
            } else {
                band_high += s;
            }
            step = step.saturating_add(1);
        }

        let total = band_low + band_mid + band_high;
        if total < 1e-6 {
            return 0.0;
        }

        let p1 = (band_low / total).max(1e-6);
        let p2 = (band_mid / total).max(1e-6);
        let p3 = (band_high / total).max(1e-6);

        -(p1 * p1.ln() + p2 * p2.ln() + p3 * p3.ln())
    }

    pub fn analyze_frame(&mut self, frame: &[i16], media_state: &MediaPlaybackState) -> VadResult {
        let rms = Self::compute_rms(frame);
        let _zcr = Self::compute_zero_crossing_rate(frame);
        let entropy = Self::compute_spectral_entropy(frame);

        let threshold = self
            .suppressor
            .compute_adaptive_vad_threshold(self.base_energy_threshold, media_state);

        if rms < threshold {
            if self.hangover_remaining > 0 {
                self.hangover_remaining = self.hangover_remaining.saturating_sub(1);
                return VadResult {
                    decision: VadDecision::Speech,
                    speech_confidence: 0.55,
                    energy_rms: rms,
                    is_speech: true,
                    reason_code: "vad_hangover".to_string(),
                };
            }

            self.speech_frame_count = 0;
            return VadResult {
                decision: VadDecision::Silence,
                speech_confidence: 0.0,
                energy_rms: rms,
                is_speech: false,
                reason_code: "vad_silence".to_string(),
            };
        }

        if media_state.is_active
            && (rms <= (media_state.reference_energy * 2.5).max(threshold) || entropy > 1.0)
        {
            self.speech_frame_count = 0;
            return VadResult {
                decision: VadDecision::MusicOrBackground,
                speech_confidence: 0.15,
                energy_rms: rms,
                is_speech: false,
                reason_code: "vad_suppressed_music".to_string(),
            };
        }

        self.speech_frame_count = self.speech_frame_count.saturating_add(1);

        if self.speech_frame_count >= self.min_speech_frames {
            self.hangover_remaining = self.hangover_frames;
            let conf = ((rms / threshold) * 0.45 + (1.1 - entropy) * 0.55).clamp(0.5, 0.99);

            VadResult {
                decision: VadDecision::Speech,
                speech_confidence: conf,
                energy_rms: rms,
                is_speech: true,
                reason_code: "vad_speech_detected".to_string(),
            }
        } else {
            VadResult {
                decision: VadDecision::Speech,
                speech_confidence: 0.4,
                energy_rms: rms,
                is_speech: true,
                reason_code: "vad_pre_speech".to_string(),
            }
        }
    }

    pub fn reset(&mut self) {
        self.speech_frame_count = 0;
        self.hangover_remaining = 0;
    }
}
