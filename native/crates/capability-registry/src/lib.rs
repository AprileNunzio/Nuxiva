#![forbid(unsafe_code)]

mod contract;
mod error;
mod registry;
mod search;
mod types;

pub use contract::{
    Contract, MAX_ID_BYTES, MAX_INPUTS, MAX_SUMMARY_BYTES, MAX_SUMMARY_TOKENS, MAX_TAGS, Param,
    token_estimate,
};
pub use error::{RegistryError, RegistryResult};
pub use registry::{
    DOCUMENT_SCHEMA, Document, Hit, MAX_CAPABILITIES, MAX_DOCUMENT_BYTES, Registry,
};
pub use search::tokenize;
pub use types::{Effect, Origin, Role, State, ValueType};

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects
)]
mod tests;
