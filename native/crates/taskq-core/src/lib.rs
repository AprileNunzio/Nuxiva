#![forbid(unsafe_code)]

mod cancel;
mod engine;
mod error;
mod journal;
mod limits;
mod queue;
mod settings;
mod spec;

pub use cancel::{CancelToken, Progress};
pub use engine::{BoxFuture, Clock, Engine, Executor, Stats, SystemClock};
pub use error::{TaskqError, TaskqResult};
pub use journal::{FileJournal, Journal, MemoryJournal};
pub use limits::Ceilings;
pub use queue::{Change, ClassCounts, Dispatch, Queue, Submitted};
pub use settings::{ClassLimits, Settings};
pub use spec::{
    Budget, Class, ErrorPayload, Risk, SCHEMA_VERSION, TaskEvent, TaskSpec, TaskState, valid_ident,
};

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::arithmetic_side_effects,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::field_reassign_with_default,
    clippy::cast_possible_truncation,
    clippy::cast_sign_loss,
    clippy::duration_suboptimal_units
)]
mod tests;
#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::arithmetic_side_effects,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::field_reassign_with_default,
    clippy::cast_possible_truncation,
    clippy::cast_sign_loss,
    clippy::duration_suboptimal_units
)]
mod tests_engine;
