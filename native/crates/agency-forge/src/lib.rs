pub mod ast_guard;
pub mod catalog;
pub mod error;
pub mod manifest;
pub mod pipeline;

#[cfg(test)]
mod tests;

pub use ast_guard::{
    ALLOWED_IMPORTS, GuardVerdict, MAX_SOURCE_BYTES, MAX_SOURCE_LINES, inspect_tool_source,
    validate_tool_name,
};
pub use catalog::{AUTO_QUARANTINE_FAILURES, ForgeCatalog, MAX_CATALOG_TOOLS};
pub use error::ForgeError;
pub use manifest::{
    ForgedToolRecord, ForgedToolSpec, MAX_TESTS, MIN_TESTS, ToolStatus, ToolTestCase,
};
pub use pipeline::{SynthesisDiagnosis, diagnose_failure, values_equivalent};
