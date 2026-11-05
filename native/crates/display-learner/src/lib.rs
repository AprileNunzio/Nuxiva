#![forbid(unsafe_code)]

pub mod context;
pub mod error;
pub mod guard;
pub mod learner;
pub mod model;
pub mod placement;
pub mod policy;
pub mod profile;
pub mod signal;
pub mod store;

pub use context::{Activity, ContextVector, ScreenRole};
pub use error::LearnError;
pub use learner::{Affinity, Learner};
pub use policy::LearnerPolicy;
pub use profile::{Metrics, Profile};
pub use signal::{FeedbackSample, Kind};

#[cfg(test)]
mod tests;
#[cfg(test)]
mod tests_store;
