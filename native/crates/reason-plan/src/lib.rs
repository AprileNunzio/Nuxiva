#![forbid(unsafe_code)]

mod error;
mod plan;
mod shadow;
mod validate;

pub use error::{PlanError, PlanResult};
pub use plan::{Arg, MAX_PLAN_BYTES, MAX_STEPS, Plan, Step, parse};
pub use shadow::{Agreement, compare};
pub use validate::{Validated, validate};

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects
)]
mod tests;
