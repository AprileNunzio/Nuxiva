#![forbid(unsafe_code)]

mod catalog;
mod error;
mod node;
mod plan;
mod quant;

pub use catalog::{Catalog, MAX_CATALOG_BYTES, MAX_MODELS, Model};
pub use error::{FitError, FitResult};
pub use node::{Device, Node, NodeClass, SATELLITE_MAX_PARAMS_M};
pub use plan::{Fit, Need, memory_mb, plan, profile};
pub use quant::Quant;

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects
)]
mod tests;
