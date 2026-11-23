#![forbid(unsafe_code)]

pub mod block;
pub mod chain;
pub mod error;
pub mod ledger;
pub mod lookup;
pub mod store;
pub mod sync;
pub mod wire;

pub use block::Block;
pub use chain::{Applied, Chain};
pub use error::{LedgerError, LedgerResult};
pub use ledger::{Head, Ledger};
pub use lookup::{Action, Lookup, reconnect_delay_ms};
pub use sync::MergeReport;
pub use wire::Wire;

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects,
    clippy::panic
)]
mod tests;

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects,
    clippy::panic
)]
mod tests_lookup;
