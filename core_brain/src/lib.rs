#![forbid(unsafe_code)]

mod dispatch;
mod embedder;
mod error;
mod fbank;
mod gate;
mod memory;
mod model;
mod router;
mod sensory;
mod supervisor;
mod worker;

pub use dispatch::{Dispatched, Dispatcher};
pub use embedder::{EMBEDDING_DIM, OnnxEmbedder};
pub use error::{BrainError, BrainResult};
pub use fbank::{Fbank, MELS, SAMPLE_RATE};
pub use gate::{GateVerdict, Gatekeeper};
pub use memory::{HotMemory, UserContext};
pub use model::{ModelSpec, SPEAKER_MODEL, digest_hex};
pub use router::{Outcome, route};
pub use sensory::{Decision, Embedder, Frame, Layer, SensoryPipeline, SharedPipeline};
pub use supervisor::{Event, Supervisor, SupervisorConfig};
pub use worker::{McpWorker, Pending, Utterance};

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::arithmetic_side_effects,
    clippy::indexing_slicing
)]
mod tests;
#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::arithmetic_side_effects,
    clippy::indexing_slicing
)]
mod tests_dispatch;
#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::arithmetic_side_effects,
    clippy::indexing_slicing,
    clippy::cast_precision_loss,
    clippy::cast_possible_truncation,
    clippy::cast_sign_loss
)]
mod tests_model;
