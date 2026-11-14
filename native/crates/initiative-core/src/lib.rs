#![forbid(unsafe_code)]

mod catalog;
mod engine;
mod error;
mod settings;

pub use catalog::{ActionTemplate, Catalog, Level, Observer, Source, subject_ok};
pub use engine::{Context, Engine, Event, Mode, Proposal, Stats};
pub use error::{InitiativeError, InitiativeResult};
pub use settings::{MAX_PAYLOAD, Settings, Situation};

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::arithmetic_side_effects,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::field_reassign_with_default,
    clippy::cast_possible_truncation
)]
mod tests;
