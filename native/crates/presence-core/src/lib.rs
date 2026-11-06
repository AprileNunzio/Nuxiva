#![forbid(unsafe_code)]

pub mod fusion;
pub mod policy;
pub mod signal;
pub mod tracker;
pub mod visibility;

pub use fusion::{Member, Proof, Reading, fuse, fuse_held, recognised, utterances};
pub use nuxiva_display_domain::{AudienceKind, Sensitivity};
pub use policy::Policy;
pub use signal::{Face, Liveness, Signals, Vision, Voice};
pub use tracker::{Audience, Tracker};
pub use visibility::{Show, widget_visible};

#[cfg(test)]
mod tests;
#[cfg(test)]
mod tests_doubt;
#[cfg(test)]
mod tests_visibility;
#[cfg(test)]
mod tests_vouch;
