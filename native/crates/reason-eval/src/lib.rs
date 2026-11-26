#![forbid(unsafe_code)]

mod compare;
mod dataset;
mod error;
mod fingerprint;
mod model;
mod report;
mod score;

pub use compare::{Comparison, Delta, Gates, Regression, Trend, compare};
pub use dataset::{
    MIN_ADVERSARIAL_CASES, MIN_CASES, MIN_HARD_PERCENT, enforce_floor, expand, load_dir, parse,
};
pub use error::{EvalError, EvalResult};
pub use fingerprint::fingerprint;
pub use model::{
    Case, Category, Effect, Expected, LANGUAGES, MAX_EXTERNAL_BYTES, MAX_TEXT_BYTES, Outcome,
    Scenario,
};
pub use report::{Report, Slice, build, parse_outcomes};
pub use score::{Verdict, judge};

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects
)]
mod tests;

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects
)]
mod compare_tests;
