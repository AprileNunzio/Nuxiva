#![forbid(unsafe_code)]

mod engine;
mod error;
mod policy;
mod widget;

pub use engine::{Decision, Engine, Subject, Why};
pub use error::{PolicyError, PolicyResult};
pub use policy::{ContextRule, MAX_PATTERNS, MAX_POLICY_BYTES, Policy, UserRule, matches};
pub use widget::{Widget, visible};

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects
)]
mod tests;
