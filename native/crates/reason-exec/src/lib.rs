#![forbid(unsafe_code)]

mod error;
mod executor;
mod journal;
mod outcome;
mod port;

pub use error::{ExecError, ExecResult};
pub use executor::{Executor, MAX_ATTEMPTS, MAX_OUTPUT_BYTES};
pub use journal::{Journal, MemoryJournal, Record, step_key};
pub use outcome::{Report, Status, StepReport};
pub use port::{ApprovalGate, Call, Cancel, Failure, Invoker, Never};

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects
)]
mod tests;
