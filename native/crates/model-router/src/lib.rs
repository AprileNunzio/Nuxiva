#![forbid(unsafe_code)]

mod budget;
mod cache;
mod compact;
mod error;
mod profile;
mod router;

pub use budget::Budget;
pub use cache::{Cache, cache_key};
pub use compact::{MAX_PROMPT_BYTES, compact, estimate_tokens};
pub use error::{RouteError, RouteResult};
pub use profile::{Placement, Profile, Sensitivity, Task};
pub use router::{Decision, MIN_QUALITY_BPS, Request, Router};

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects
)]
mod tests;
