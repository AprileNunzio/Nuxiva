#![forbid(unsafe_code)]

mod catalog;
mod error;
mod settings;
mod store;
mod wire;

pub use catalog::{Catalog, KindSpec, name_ok};
pub use error::{ReflectError, ReflectResult};
pub use settings::{MAX_PAYLOAD, Settings};
pub use store::{Recorded, Store, Verification};
pub use wire::{
    Candidate, Delta, Lesson, LessonState, MAX_OBSERVED, Observed, Outcome, Reflection,
    SCHEMA_VERSION, Signals,
};

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
#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::arithmetic_side_effects,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::field_reassign_with_default,
    clippy::cast_possible_truncation
)]
mod tests_more;
