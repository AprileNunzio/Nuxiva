#![forbid(unsafe_code)]

pub mod beacon;
pub mod discovery;
pub mod throttle;

pub use beacon::{Beacon, MAX_DATAGRAM, decode, encode};
pub use discovery::Discovery;
pub use throttle::Throttle;

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects,
    clippy::panic
)]
mod tests;
