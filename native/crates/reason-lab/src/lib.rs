#![forbid(unsafe_code)]

mod backend;
mod custom;
pub mod facade;
mod outcome;

pub use backend::Backend;
pub use custom::{
    Inspection, MAX_DATASET_BYTES, MAX_LANGUAGES, MAX_SCENARIOS, expand_custom, inspect,
    parse_scenarios,
};
pub use outcome::to_outcome;

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects
)]
mod run_tests;

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects
)]
mod tests;
