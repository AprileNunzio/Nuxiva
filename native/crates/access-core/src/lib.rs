#![forbid(unsafe_code)]

pub mod capability;
pub mod cell;
pub mod decide;
pub mod error;
pub mod floor;
pub mod matrix;
pub mod role;
pub mod smb_sync;

pub use capability::Capability;
pub use cell::Cell;
pub use decide::{Request, Strength, Verdict, decide};
pub use error::AccessError;
pub use matrix::Matrix;
pub use role::Role;

#[cfg(test)]
mod tests;
#[cfg(test)]
mod tests_matrix;
