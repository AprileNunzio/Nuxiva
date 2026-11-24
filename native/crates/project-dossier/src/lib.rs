#![forbid(unsafe_code)]

mod doc;
mod dossier;
mod error;

pub use doc::{Doc, MAX_FILE_BYTES, MAX_SECTIONS, Section, parse};
pub use dossier::{Dossier, MAX_SELECTION_TOKENS, Picked, REQUIRED, SectionRef, skeleton};
pub use error::{DossierError, DossierResult};

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects
)]
mod tests;
