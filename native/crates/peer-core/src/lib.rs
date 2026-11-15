#![forbid(unsafe_code)]

pub mod addr;
pub mod capability;
pub mod directory;
pub mod election;
pub mod envelope;
pub mod error;
pub mod gossip;
pub mod ident;
pub mod job;
pub mod message;
pub mod registry;
pub mod scheduler;
pub mod score;

pub use capability::{Capabilities, Load, Roles, Tier};
pub use directory::Directory;
pub use envelope::{Envelope, PeerKey, TrustBook, Verifier};
pub use error::{PeerError, PeerResult};
pub use gossip::Gossip;
pub use job::{JobSpec, Kind, Needs};
pub use message::Message;
pub use registry::{Liveness, Registry, Status};
pub use scheduler::{Decision, Phase, Reason, Scheduler};

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects,
    clippy::panic,
    clippy::match_wildcard_for_single_variants
)]
mod tests;
