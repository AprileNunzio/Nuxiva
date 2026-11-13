#![forbid(unsafe_code)]

mod align;
mod array;
pub mod danger_sound;
mod denoiser;
pub mod distress;
mod distress_phrases;
pub mod endpoint;
mod features;
mod gain;
mod level;
mod music_room;
mod noise;
mod scene;
mod sound_frame;
mod speaker;
mod stft;
mod voices;
pub mod vote;
pub mod wake;
pub mod words;

pub use align::{ALIGN_WINDOW, Alignment, MAX_LAG};
pub use array::{ArrayError, ArrayFrame, MAX_ARRAY_FRAME, MAX_CHANNELS, MicArray};
pub use denoiser::{Denoiser, DenoiserConfig, clean_utterance};
pub use features::FrameFeatures;
pub use gain::{exp_integral, omlsa_gain};
pub use level::{normalize, utterance_gain, voiced_rms};
pub use music_room::{
    MAX_MICS, MusicPresence, MusicRoom, PRESENCE_OFF_MS, PRESENCE_ON_MS, PROBE_BUSY_MS,
    PROBE_MAX_WAIT_MS, PROBE_MIN_WAIT_MS, ProbeClock, RoomChange, RoomStep,
};
pub use noise::{Mcra, NoiseTracker};
pub use scene::{SceneClassifier, SceneVerdict, SoundKind};
pub use speaker::{MAX_DIM, MAX_PEOPLE, MAX_ROWS, Verdict, VoiceBook, VoicePolicy, valid_slug};
pub use stft::{BINS, HOP, N_FFT, RATE, Spectrum, Stft};
pub use voices::{MAX_VOICES, TurnInfo, VoiceTracker, split_turns};

pub const MAX_STREAM_SAMPLES: usize = 512 * 1024;
pub const MAX_UTTERANCE_SAMPLES: usize = 16_000 * 600;

#[cfg(test)]
mod array_tests;
#[cfg(test)]
mod danger_tests;
#[cfg(test)]
mod music_room_tests;
#[cfg(test)]
mod scene_tests;
#[cfg(test)]
mod speaker_tests;
#[cfg(test)]
mod tests;
#[cfg(test)]
mod words_tests;
