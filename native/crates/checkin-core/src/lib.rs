#![forbid(unsafe_code)]

mod affinity;
mod error;
mod model;
mod phatic;
mod plan;
mod text;

pub use affinity::{Entry, Observation, Observe, Told, observe, weight};
pub use error::{CheckinError, CheckinResult};
pub use model::{Fact, Kind, MAX_FACTS, MAX_TURNS, Moment, Request, Turn};
pub use phatic::{PHATIC, Phatic, detect};
pub use plan::{Chosen, Daypart, Plan, REUSE_WINDOW, Tone, URGENT, daypart, plan};

#[cfg(test)]
#[allow(clippy::expect_used, clippy::panic, clippy::indexing_slicing)]
mod tests;

#[cfg(test)]
#[allow(clippy::expect_used, clippy::panic, clippy::indexing_slicing)]
mod tests_affinity;
