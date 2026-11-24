#![forbid(unsafe_code)]

mod backend;
mod outcome;

pub use backend::Backend;
pub use outcome::to_outcome;

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects
)]
mod tests;
