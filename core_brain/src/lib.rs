#![forbid(unsafe_code)]

mod bootstrap;
mod dispatch;
mod ear_link;
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

pub use bootstrap::{Paths, apply_signed_catalog, build_hub, card_of, load_agents};
pub use dispatch::{Dispatched, Dispatcher};
pub use ear_link::{EarEndpoint, parse as parse_ear, run as run_ear};
pub use embedder::{EMBEDDING_DIM, OnnxEmbedder};
pub use error::{BrainError, BrainResult};
pub use fbank::{Fbank, MELS, SAMPLE_RATE};
pub use gate::{GateVerdict, Gatekeeper};
pub use memory::{HotMemory, UserContext};
pub use model::{ModelSpec, SPEAKER_MODEL, digest_hex};
pub use router::{Outcome, route};
pub use sensory::{Decision, Embedder, Frame, Layer, SensoryPipeline, SharedPipeline};
pub use supervisor::{Event, Supervisor, SupervisorConfig};
pub use worker::{Declared, McpWorker, Pending, Utterance, arguments_for};

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
    clippy::indexing_slicing,
    clippy::panic
)]
mod tests_bridge;
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
