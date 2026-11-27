#![forbid(unsafe_code)]

mod cues;
mod error;
mod fuzzy;
mod intent;
mod inventory;
mod lexicon;
mod resolve;
mod signals;
mod text;

pub use error::{ResolveError, ResolveResult};
pub use fuzzy::{distance, similarity};
pub use intent::{Purpose, RELEVANT, Relevance};
pub use inventory::{Area, Entity, Inventory, MAX_AREAS, MAX_ENTITIES, MAX_INVENTORY_BYTES};
pub use lexicon::Action;
pub use resolve::{
    CONFIRM, Call, Decision, EXECUTE, MAX_TEXT_BYTES, Request, Resolution, Resolver, action_of,
};
pub use text::{normalize, stem};

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects
)]
mod tests;

#[cfg(test)]
#[allow(clippy::expect_used, clippy::panic, clippy::indexing_slicing)]
mod tests_intent;
