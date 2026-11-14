#![forbid(unsafe_code)]

mod error;
mod fuser;
mod fusion;
mod observation;
mod settings;
mod source;

pub use error::{PerceptError, PerceptResult};
pub use fuser::Fuser;
pub use fusion::Fusion;
pub use observation::Observation;
pub use settings::PerceptSettings;
pub use source::{PerceptSource, QueueSource};

#[cfg(test)]
#[allow(clippy::expect_used, clippy::arithmetic_side_effects)]
mod tests;
#[cfg(test)]
#[allow(clippy::expect_used, clippy::arithmetic_side_effects)]
mod tests_chaos;
