#![forbid(unsafe_code)]

mod barge;
mod chunker;
mod error;
mod frame;
mod pipeline;
mod session;
mod settings;
mod state;

pub use barge::{
    Backchannel, BargeDetector, BargeSettings, BargeStats, Decision, Evidence, PreRoll, Risk,
    Verdict, may_command,
};
pub use chunker::{Backlog, ChunkSettings, Chunker};
pub use error::{DuplexError, DuplexResult};
pub use frame::{AUDIO_HEADER, AUDIO_KIND, Audio, Control};
pub use pipeline::{Metrics, Pipeline, Synth};
pub use session::{CutReport, Event, EventKind, Interruption, Session, Snapshot};
pub use settings::{MAX_SETTINGS_BYTES, PROTOCOL_VERSION, Settings};
pub use state::{State, Trigger};

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
    clippy::indexing_slicing,
    clippy::field_reassign_with_default,
    clippy::cast_possible_truncation
)]
mod tests_stream;
