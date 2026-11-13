#![forbid(unsafe_code)]

mod catalog;
mod error;
mod limits;
mod settings;
pub mod wire;

pub use catalog::{Catalog, WorkerTemplate, intent_slug};
pub use error::{SwarmError, SwarmResult};
pub use limits::Ceilings;
pub use settings::Settings;
pub use wire::{
    Affect, Channel, Constraints, Digest, Edge, Ident, Level, Outcome, Percept, Phase, Plan,
    SCHEMA_VERSION, Step, StepBudget, StepEvent, TaskEnvelope, Usage, Validate, VerifySpec,
    WorkerError, WorkerErrorKind, WorkerResult, decode, encode,
};

#[cfg(test)]
mod tests;
#[cfg(test)]
mod tests_arch;
#[cfg(test)]
mod tests_fuzz;
