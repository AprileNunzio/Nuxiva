#![forbid(unsafe_code)]

pub mod hippocampus;
pub mod platform;
pub mod slots;

pub use hippocampus::index::NeuronIndex;
pub use hippocampus::types::{Decision, SlowReason, Thresholds, Verdict};
pub use platform::error::{CortexError, CortexResult};
pub use slots::types::{SlotDefinition, SlotType, SlotValue};
