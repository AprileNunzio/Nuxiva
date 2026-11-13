#![forbid(unsafe_code)]

mod buffer;
mod policy;

pub use buffer::{
    FrameMeta, Hit, Indicator, MAX_DIM, MAX_FRAMES, PushOutcome, Source, VisualBuffer,
};
pub use policy::{DEFAULT_SENSITIVE, Policy, Rejection};

#[cfg(test)]
mod tests;
