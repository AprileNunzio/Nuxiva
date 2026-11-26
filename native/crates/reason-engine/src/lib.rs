#![forbid(unsafe_code)]

mod cache;
mod catalog;
mod config;
mod engine;
mod error;
mod journal;
mod ledger;
mod mode;
mod prompt;

pub use cache::{PlanCache, shape_key};
pub use catalog::{MAX_QUERY_BYTES, line, query, render, retrieve};
pub use config::{Config, DAY_MS, Gate, MAX_CONFIG_BYTES};
pub use engine::{Checked, Engine, Prepared, Verdict, plan_hash};
pub use error::{EngineError, EngineResult};
pub use journal::{MAX_JOURNAL_BYTES, SealedJournal};
pub use ledger::{Bucket, GateStatus, KEEP_DAYS, Ledger, MAX_LEDGER_BYTES, Sample};
pub use mode::{Mode, Switch};
pub use prompt::{PLAN_SCHEMA, PLAN_SYSTEM, PlanRequest, build, goal_shape};

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects
)]
mod tests;
