pub mod batch;
pub mod error;
pub mod patch;
pub mod verify;
pub mod worktree;

#[cfg(test)]
mod tests;

pub use batch::{ActionItem, ActionKind, BatchPlan, ExecutionWave, plan_parallel_batch};
pub use error::ActionError;
pub use patch::{
    LineRangeView, PatchOutcome, ReplacementChunk, apply_surgical_patches, view_line_range,
};
pub use verify::{GateVerdict, evaluate_gate};
pub use worktree::{MergeReport, StagedEdit, WorkspaceCoordinator};
