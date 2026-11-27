#![forbid(unsafe_code)]

mod error;
mod model;
mod phatic;
mod plan;
mod text;

pub use error::{CheckinError, CheckinResult};
pub use model::{Fact, Kind, MAX_FACTS, MAX_TURNS, Moment, Request, Turn};
pub use phatic::{PHATIC, Phatic, detect};
pub use plan::{Chosen, Daypart, Plan, REUSE_WINDOW, Tone, URGENT, daypart, plan};

#[cfg(test)]
#[allow(clippy::expect_used, clippy::panic, clippy::indexing_slicing)]
mod tests;
