#![forbid(unsafe_code)]

mod error;
mod forge;
mod sandbox;

pub use error::{ForgeError, ForgeResult};
pub use forge::{
    Forge, MAX_ARTIFACT_BYTES, MAX_CANDIDATES, MAX_PROBES, MAX_RUN_MILLIS, MIN_PROBES,
    SHADOW_STREAK, Stage,
};
pub use sandbox::{Artifact, Expect, Kind, Observation, Probe, Sandbox, SandboxError};

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects
)]
mod tests;
