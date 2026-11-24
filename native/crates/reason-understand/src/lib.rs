#![forbid(unsafe_code)]

mod error;
mod goal;
mod prompt;
mod understand;

pub use error::{UnderstandError, UnderstandResult};
pub use goal::{
    Entity, Goal, MAX_CONSTRAINTS, MAX_ENTITIES, MAX_RAW_BYTES, MAX_VALUE_BYTES, RawGoal, Risk,
    Source, parse, risk_of,
};
pub use prompt::{CLOSE, OPEN, Request, SCHEMA, SYSTEM, build};
pub use understand::{DEFAULT_THRESHOLD_BPS, MAX_USER_BYTES, Model, Understander, Understood};

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects
)]
mod tests;
