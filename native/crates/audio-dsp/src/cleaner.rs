use crate::filter::BandpassFilter300_3400;
use crate::media_awareness::{AcousticEchoSuppressor, MediaPlaybackState};
use crate::vad::{SpectralEntropyVad, VadResult};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CleanedFrame {
    pub pcm_clean: Vec<i16>,
    pub vad: VadResult,
    pub is_gated: bool,
    pub attenuation_applied: f32,
    pub frame_samples: usize,
}

#[derive(Debug, Clone, PartialEq)]
pub struct AudioCleaner {
    filter: BandpassFilter300_3400,
    suppressor: AcousticEchoSuppressor,
    vad: SpectralEntropyVad,
    buffer_scratch: Vec<i16>,
}

impl Default for AudioCleaner {
    fn default() -> Self {
        Self::new()
    }
}

impl AudioCleaner {
    #[must_use]
    pub fn new() -> Self {
        Self {
            filter: BandpassFilter300_3400::new(),
            suppressor: AcousticEchoSuppressor::new(),
            vad: SpectralEntropyVad::default(),
            buffer_scratch: Vec::with_capacity(640),
        }
    }

    pub fn process_frame(
        &mut self,
        raw_pcm: &[i16],
        media_state: &MediaPlaybackState,
    ) -> CleanedFrame {
        self.filter
            .process_buffer(raw_pcm, &mut self.buffer_scratch);

        let vad_result = self.vad.analyze_frame(&self.buffer_scratch, media_state);

        let factor = self.suppressor.compute_suppression_factor(media_state);

        let is_gated = !vad_result.is_speech;

        let mut pcm_clean = Vec::with_capacity(self.buffer_scratch.len());

        if is_gated {
            pcm_clean.resize(self.buffer_scratch.len(), 0);
        } else if (factor - 1.0).abs() > 0.01 {
            for &sample in &self.buffer_scratch {
                let scaled = (f32::from(sample) * factor).clamp(-32_768.0, 32_767.0);
                #[allow(clippy::cast_possible_truncation)]
                let scaled_i16 = scaled as i16;
                pcm_clean.push(scaled_i16);
            }
        } else {
            pcm_clean.extend_from_slice(&self.buffer_scratch);
        }

        let frame_samples = pcm_clean.len();

        CleanedFrame {
            pcm_clean,
            vad: vad_result,
            is_gated,
            attenuation_applied: if is_gated { 0.0 } else { factor },
            frame_samples,
        }
    }

    pub fn reset(&mut self) {
        self.filter.reset();
        self.vad.reset();
        self.buffer_scratch.clear();
    }
}
