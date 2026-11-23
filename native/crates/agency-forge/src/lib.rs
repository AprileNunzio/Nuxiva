pub mod ast_guard;
pub mod catalog;
pub mod error;
pub mod healing;
pub mod manifest;
pub mod permissions;
pub mod pipeline;
pub mod sandbox;

#[cfg(test)]
mod tests;

pub use ast_guard::{
    ALLOWED_IMPORTS, GuardVerdict, MAX_SOURCE_BYTES, MAX_SOURCE_LINES, inspect_tool_source,
    validate_tool_name,
};
pub use catalog::{AUTO_QUARANTINE_FAILURES, ForgeCatalog, MAX_CATALOG_TOOLS};
pub use error::ForgeError;
pub use healing::{
    FailureCause, FailureContext, MAX_REPAIR_ATTEMPTS, RepairStrategy, SelfHealingPlan,
    formulate_healing_plan,
};
pub use manifest::{
    ForgedToolRecord, ForgedToolSpec, MAX_TESTS, MIN_TESTS, ToolStatus, ToolTestCase,
};
pub use permissions::{Access, MAX_SCOPES, ToolPermissions};
pub use pipeline::{SynthesisDiagnosis, diagnose_failure, values_equivalent};
pub use sandbox::{
    MAX_STDOUT_BYTES, MAX_WALL_MS, SandboxExecutionOutcome, VerificationProof,
    verify_sandbox_outcomes,
};
