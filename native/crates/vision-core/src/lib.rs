#![forbid(unsafe_code)]

mod buffer;
mod cadence;
mod policy;

pub use buffer::{
    FrameMeta, Hit, Indicator, MAX_DIM, MAX_FRAMES, PushOutcome, Source, VisualBuffer,
};
pub use cadence::{Cadence, THUMB_H, THUMB_W, Verdict, dhash};
pub use policy::{DEFAULT_SENSITIVE, Policy, Rejection};

#[cfg(test)]
mod tests;
#[cfg(test)]
#[allow(clippy::arithmetic_side_effects)]
mod tests_cadence;
