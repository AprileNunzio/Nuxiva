#![forbid(unsafe_code)]

mod audit;
mod error;
mod inventory;
mod model;
mod scanner;

pub use audit::{Chain, Entry};
pub use error::{InventoryError, InventoryResult};
pub use inventory::{DEFAULT_GRACE_MS, Inventory};
pub use model::{Diff, Found, Item, Kind, Origin, Snapshot, State};
pub use scanner::{DirScanner, MAX_ENTRIES, MAX_MANIFEST_BYTES, Scanner};

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects
)]
mod tests;
