#![forbid(unsafe_code)]

pub mod danger_sound;
mod denoiser;
pub mod distress;
mod distress_phrases;
mod features;
mod gain;
mod level;
mod noise;
mod scene;
mod sound_frame;
mod speaker;
mod stft;
mod voices;
pub mod wake;
pub mod words;

pub use denoiser::{Denoiser, DenoiserConfig, clean_utterance};
pub use features::FrameFeatures;
pub use gain::{exp_integral, omlsa_gain};
pub use level::{normalize, utterance_gain, voiced_rms};
pub use noise::{Mcra, NoiseTracker};
pub use scene::{SceneClassifier, SceneVerdict, SoundKind};
pub use speaker::{MAX_DIM, MAX_PEOPLE, MAX_ROWS, Verdict, VoiceBook, VoicePolicy, valid_slug};
pub use stft::{BINS, HOP, N_FFT, RATE, Spectrum, Stft};
pub use voices::{MAX_VOICES, TurnInfo, VoiceTracker, split_turns};

pub const MAX_STREAM_SAMPLES: usize = 512 * 1024;
pub const MAX_UTTERANCE_SAMPLES: usize = 16_000 * 600;

#[cfg(test)]
mod danger_tests;
#[cfg(test)]
mod scene_tests;
#[cfg(test)]
mod speaker_tests;
#[cfg(test)]
mod tests;
#[cfg(test)]
mod words_tests;
