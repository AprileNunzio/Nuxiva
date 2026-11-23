#![allow(unsafe_code)]

uniffi::setup_scaffolding!();

pub mod announce;
pub mod enroll;
pub mod error;
pub mod identity;
pub mod trust;

pub use announce::{DeviceFacts, heartbeat_body};
pub use enroll::{EnrollmentPayload, normalize_code, normalize_server_input, parse_enrollment};
pub use error::MobileError;
pub use identity::{DeviceIdentity, SignedRequest, new_node_id};
pub use trust::{ca_der, ca_fingerprint, pin_matches};

#[cfg(test)]
#[allow(clippy::expect_used, clippy::indexing_slicing, clippy::unwrap_used)]
mod tests;
