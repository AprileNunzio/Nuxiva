#![forbid(unsafe_code)]

pub mod error;
pub mod index;
pub mod look;
pub mod ops;
pub mod profile;
pub mod retention;
pub mod search;
pub mod sighting;
pub mod store;

pub use error::MemoryError;
pub use index::IndexKey;
pub use look::{Build, Color, Headwear, Item, Look, Vehicle, VehicleKind};
pub use profile::Profile;
pub use retention::Policy;
pub use search::{Page, Search};
pub use sighting::{Audience, Class, Evidence, EvidenceKind, Sighting, Who};

#[cfg(test)]
mod tests;
#[cfg(test)]
mod tests_store;
