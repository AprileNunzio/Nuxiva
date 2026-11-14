#![forbid(unsafe_code)]

mod barge;
mod chunker;
mod error;
mod frame;
mod gate;
mod merge;
mod pacer;
mod pipeline;
mod session;
mod settings;
mod state;
mod wav;
mod window;

pub use barge::{
    Backchannel, BargeDetector, BargeSettings, BargeStats, Decision, Evidence, PreRoll, Risk,
    Verdict, may_command,
};
pub use chunker::{Backlog, ChunkSettings, Chunker};
pub use error::{DuplexError, DuplexResult};
pub use frame::{AUDIO_HEADER, AUDIO_KIND, Audio, Control};
pub use gate::{
    AttributionChain, MAX_FRAME_SAMPLES, MAX_PENDING_SAMPLES, MAX_SLUG_BYTES, QUARANTINE_WINDOWS,
    WINDOW_SAMPLES, Window, WindowGate,
};
pub use merge::{Intent, IntentCatalog, InterruptedReply, MAX_SPOKEN_CHARS, Plan, words};
pub use pacer::{ChunkInfo, Dropped, MAX_FRAME_BYTES, MAX_QUEUE_FRAMES, Pacer, PacerSettings};
pub use pipeline::{Metrics, Pipeline, Synth};
pub use session::{CutReport, Event, EventKind, Interruption, Session, Snapshot};
pub use settings::{MAX_SETTINGS_BYTES, PROTOCOL_VERSION, Settings};
pub use state::{State, Trigger};
pub use wav::{MAX_RATE_HZ, MAX_WAV_BYTES, MIN_RATE_HZ, Pcm, parse_wav, samples_us};
pub use window::{
    CONFIRM_WINDOWS, KNOWN_BONUS, MIN_RUNNER_GAP, WINDOW_MS, WindowInput, judge_window,
    windowed_settings,
};

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::arithmetic_side_effects,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::field_reassign_with_default,
    clippy::cast_possible_truncation
)]
mod tests;
#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::arithmetic_side_effects,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::field_reassign_with_default
)]
mod tests_barge;
#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::arithmetic_side_effects,
    clippy::panic,
    clippy::indexing_slicing
)]
mod tests_merge;
#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::arithmetic_side_effects,
    clippy::panic,
    clippy::indexing_slicing
)]
mod tests_perf;
#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::arithmetic_side_effects,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::field_reassign_with_default,
    clippy::cast_possible_truncation
)]
mod tests_stream;
#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::arithmetic_side_effects,
    clippy::panic,
    clippy::indexing_slicing
)]
mod tests_window;

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::arithmetic_side_effects,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::cast_possible_truncation
)]
mod tests_gate;
#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::arithmetic_side_effects,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::cast_possible_truncation
)]
mod tests_pacer;
