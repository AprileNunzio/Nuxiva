#![forbid(unsafe_code)]
#![allow(
    clippy::cast_precision_loss,
    clippy::cast_possible_truncation,
    clippy::cast_sign_loss,
    clippy::many_single_char_names,
    clippy::unreadable_literal
)]

mod dtw;
pub mod error;
pub mod fusion;
pub mod handle;
pub mod mel;
pub mod model;
pub mod stream;
mod vad;

pub use error::{WakeError, WakeResult};
pub use fusion::{Decision, Policy, Speaker, decide};
pub use model::{MAX_RECORDINGS, MIN_RECORDINGS, Model};
pub use stream::{Config, Detection, Detector};
