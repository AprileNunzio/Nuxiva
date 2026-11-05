#![forbid(unsafe_code)]

pub mod cadence;
pub mod entry;
pub mod error;
pub mod health;
pub mod lifecycle;
pub mod policy;
pub mod scheduler;

pub use cadence::Cadence;
pub use error::SchedulerError;
pub use lifecycle::{Lifecycle, Transition};
pub use policy::Policy;
pub use scheduler::{Due, Scheduler, WidgetInput};

#[cfg(test)]
mod tests;
#[cfg(test)]
mod tests_budget;
