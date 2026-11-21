pub mod batch;
pub mod error;
pub mod jev_web;
pub mod patch;
pub mod preflight;
pub mod transaction;
pub mod verify;
pub mod worktree;

#[cfg(test)]
mod tests;

pub use batch::{ActionItem, ActionKind, BatchPlan, ExecutionWave, plan_parallel_batch};
pub use error::ActionError;
pub use jev_web::{
    JEV_CSP_POLICY, JEV_IFRAME_SANDBOX_FLAGS, JevFirewallVerdict, JevPhase, JevWebSessionPlan,
    JevWebStep, MAX_JEV_STEPS, MAX_URL_LEN, WebActionKind, build_google_search_jev_plan,
    build_restaurant_booking_jev_plan, evaluate_jev_firewall, sanitize_zero_trust_url,
    verify_and_advance_jev_step,
};
pub use patch::{
    LineRangeView, PatchOutcome, ReplacementChunk, apply_surgical_patches, view_line_range,
};
pub use preflight::{ActionCommandSpec, ActionInvariant, PreflightSimulator, PreflightVerdict};
pub use transaction::{ActionTransaction, FileSnapshot, TransactionStatus};
pub use verify::{GateVerdict, evaluate_gate};
pub use worktree::{MergeReport, StagedEdit, WorkspaceCoordinator};
