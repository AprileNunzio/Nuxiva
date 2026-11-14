#![forbid(unsafe_code)]

mod error;
mod gate;
mod memory;
mod sensory;
mod supervisor;

pub use error::{BrainError, BrainResult};
pub use gate::{GateVerdict, Gatekeeper};
pub use memory::{HotMemory, UserContext};
pub use sensory::{Decision, Embedder, Frame, Layer, SensoryPipeline, SharedPipeline};
pub use supervisor::{Event, Supervisor, SupervisorConfig};

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::arithmetic_side_effects,
    clippy::indexing_slicing
)]
mod tests;
