#![forbid(unsafe_code)]

mod catalog;
mod error;
mod limits;
mod settings;
mod supervisor;
pub mod wire;
mod worker;

pub use catalog::{Catalog, WorkerTemplate, intent_slug};
pub use error::{SwarmError, SwarmResult};
pub use limits::Ceilings;
pub use settings::{LevelBudget, LevelLimits, Settings};
pub use supervisor::{
    Admission, GraphGate, Offer, PlanPrompt, Planner, Request, Supervisor, check_budget,
    critical_path_ms, deterministic, level_budget, pick_intent,
};
pub use wire::{
    Affect, Channel, Constraints, Digest, Edge, Ident, Level, Outcome, Percept, Phase, Plan,
    SCHEMA_VERSION, Step, StepBudget, StepEvent, TaskEnvelope, Usage, Validate, VerifySpec,
    WorkerError, WorkerErrorKind, WorkerResult, decode, encode,
};
pub use worker::{
    Beat, BoxFuture, CODE_BUDGET, CODE_CANCELLED, CODE_DEADLINE, CODE_DEPTH, CODE_GRAPH,
    CODE_LEASE, CODE_NO_KIND, CODE_OUTPUT, CODE_PANIC, CODE_STALE, CancelToken, Executor, Factory,
    Meter, Output, Report, StepContext, StepReport, Worker,
};

#[cfg(test)]
mod tests;
#[cfg(test)]
mod tests_arch;
#[cfg(test)]
mod tests_fuzz;
#[cfg(test)]
#[allow(clippy::expect_used, clippy::arithmetic_side_effects)]
mod tests_supervisor;
#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::arithmetic_side_effects,
    clippy::panic,
    clippy::indexing_slicing
)]
mod tests_worker;
#[cfg(test)]
#[allow(clippy::expect_used, clippy::arithmetic_side_effects, clippy::panic)]
mod tests_worker_more;
#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::arithmetic_side_effects,
    clippy::panic,
    clippy::indexing_slicing
)]
mod tests_worker_support;
