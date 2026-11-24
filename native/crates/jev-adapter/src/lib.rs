#![forbid(unsafe_code)]

mod adapter;
mod model;

pub use adapter::{Adapter, BREAKER_COOLDOWN_MS, BREAKER_FAILURES};
pub use model::{
    Attachments, Classifier, Input, MAX_TEXT_BYTES, Node, Platform, Reason, Route, Unavailable,
};

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects
)]
mod tests;
