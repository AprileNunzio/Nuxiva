#![forbid(unsafe_code)]

mod engine;
mod error;
mod gate;
mod judge;
mod paths;
mod redact;
mod settings;
mod wire;

pub use engine::{Coder, Critic, Escalation, Outcome, run};
pub use error::{LoopError, LoopResult};
pub use gate::{Audit, Decision, Gate, Permit, Target, repo_ok};
pub use judge::{Judgement, judge};
pub use paths::{is_protected, normalize};
pub use redact::{normalize_for_fingerprint, redact};
pub use settings::{MAX_PAYLOAD, Settings};
pub use wire::{
    Artifact, ArtifactDraft, Check, CriticReport, Feedback, FileEntry, SCHEMA_VERSION, Severity,
    Verdict, hex, is_digest, parse,
};

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::arithmetic_side_effects,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::field_reassign_with_default
)]
mod tests;
#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::arithmetic_side_effects,
    clippy::panic,
    clippy::indexing_slicing
)]
mod tests_arch;
#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::arithmetic_side_effects,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::field_reassign_with_default
)]
mod tests_gate;
#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::arithmetic_side_effects,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::field_reassign_with_default
)]
mod tests_misc;
