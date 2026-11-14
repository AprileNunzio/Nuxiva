#![forbid(unsafe_code)]

pub mod announce;
pub mod audit;
pub mod authorize;
pub mod declare;
pub mod error;
pub mod hexutil;
pub mod identity;
pub mod profile;
pub mod scope;
pub mod signer;

pub use announce::{Announce, Hardware};
pub use audit::Entry;
pub use authorize::{Verdict, authorize, effective};
pub use declare::{Facts, declare};
pub use error::NodeError;
pub use profile::{Ceiling, Mode, Profile, resolve};
pub use signer::{DeviceKey, SignedHeaders, random_nonce};

#[cfg(test)]
#[allow(clippy::expect_used, clippy::indexing_slicing)]
mod tests;
#[cfg(test)]
#[allow(clippy::expect_used, clippy::indexing_slicing)]
mod tests_declare;
#[cfg(test)]
#[allow(clippy::expect_used, clippy::indexing_slicing)]
mod tests_identity;
#[cfg(test)]
#[allow(clippy::expect_used, clippy::indexing_slicing)]
mod tests_signer;
