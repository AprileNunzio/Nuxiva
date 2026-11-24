#![forbid(unsafe_code)]

pub mod bridge;
pub mod capture;
pub mod config;
pub mod daemon;
pub mod error;
pub mod evdev;
pub mod fb;
pub mod naming;
pub mod notice;
pub mod pathguard;
pub mod policy;
pub mod proc;
pub mod raster;
pub mod retention;
pub mod session;
pub mod sink;
pub mod smblogin;
pub mod spool;

pub use config::Config;
pub use error::{Error, Result};

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects,
    clippy::unwrap_used
)]
mod tests;
#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects,
    clippy::unwrap_used
)]
mod tests_bridge;
#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects,
    clippy::unwrap_used
)]
mod tests_io;
