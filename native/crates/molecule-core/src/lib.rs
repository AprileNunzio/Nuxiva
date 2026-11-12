#![forbid(unsafe_code)]
pub mod bonds;
pub mod element;
pub mod error;
pub mod lod;
pub mod model;
pub mod parse;

pub use error::{MolError, MolResult};
pub use lod::{Built, ColorScheme, Lod, build};
pub use model::{Atom, SecondaryKind, SecondaryRange, Structure, Summary};
pub use parse::{Format, Limits, parse};

#[cfg(test)]
mod tests;
