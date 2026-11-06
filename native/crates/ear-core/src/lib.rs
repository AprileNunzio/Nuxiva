#![forbid(unsafe_code)]

mod denoiser;
mod features;
mod gain;
mod level;
mod noise;
mod scene;
mod stft;

pub use denoiser::{Denoiser, DenoiserConfig, clean_utterance};
pub use features::FrameFeatures;
pub use gain::{exp_integral, omlsa_gain};
pub use level::{normalize, utterance_gain, voiced_rms};
pub use noise::{Mcra, NoiseTracker};
pub use scene::{SceneClassifier, SceneVerdict, SoundKind};
pub use stft::{BINS, HOP, N_FFT, RATE, Spectrum, Stft};

pub const MAX_STREAM_SAMPLES: usize = 512 * 1024;
pub const MAX_UTTERANCE_SAMPLES: usize = 16_000 * 600;

#[cfg(test)]
mod scene_tests;
#[cfg(test)]
mod tests;
