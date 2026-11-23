#![forbid(unsafe_code)]

pub mod block;
pub mod chain;
pub mod error;
pub mod ledger;
pub mod store;
pub mod sync;

pub use block::Block;
pub use chain::{Applied, Chain};
pub use error::{LedgerError, LedgerResult};
pub use ledger::{Head, Ledger};
pub use sync::MergeReport;

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects,
    clippy::panic
)]
mod tests;
