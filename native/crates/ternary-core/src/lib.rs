pub mod cluster;
pub mod error;
pub mod graph;
pub mod index;
pub mod quantize;
pub mod sleep;
pub mod tier;
pub mod vector;

#[cfg(test)]
#[allow(
    clippy::unwrap_used,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects
)]
mod tests;

pub use cluster::{ClusterEngine, MicroCluster, SynthesisNode};
pub use error::TernaryError;
pub use graph::{EdgeType, GraphEdge, MemoryGraph};
pub use index::{TernaryIndex, TernaryRecord};
pub use quantize::quantize_dense;
pub use sleep::{SleepConsolidator, SleepReport};
pub use tier::{TierManager, TierState, TieredMemoryItem};
pub use vector::TernaryVector;
