pub mod artifact;
pub mod engine;
mod intents;
pub mod memory;
mod patterns;
pub mod smb;
mod strict;
pub mod types;

#[cfg(test)]
mod tests;

#[cfg(test)]
mod tests_strict;

#[cfg(test)]
#[allow(clippy::expect_used, clippy::panic, clippy::indexing_slicing)]
mod tests_studio;

pub use artifact::ArtifactParser;
pub use engine::ChatStudioEngine;
pub use intents::{CONVERSATION, Intent, IntentError, IntentTable};
pub use memory::CrossMemoryVault;
pub use smb::{SmbGuardError, SmbPathGuard, SmbShareCategory};
pub use strict::{Outcome, StrictReply};
pub use types::{
    Artifact, Attachment, AttachmentKind, MemoryFact, MemorySource, Message, Project, Role, Thread,
};
