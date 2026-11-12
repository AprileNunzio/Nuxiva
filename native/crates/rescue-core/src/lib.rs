#![forbid(unsafe_code)]

mod action;
mod detect;
mod escalation;
mod fusion;
mod policy;
mod signal;

pub use action::{Action, Entry, Stage, Step, Tone};
pub use detect::detect_visual;
pub use escalation::{Engine, MAX_TIMELINE};
pub use fusion::{Assessment, Driver, HazardRisk, assess};
pub use policy::{Policy, PolicyError, Sensitivity};
pub use signal::{Evidence, EvidenceError, Hazard, Kind, MAX_EVIDENCE, MAX_SOURCE, Modality};

#[cfg(test)]
mod escalation_tests;
#[cfg(test)]
mod fusion_tests;
#[cfg(test)]
mod policy_tests;
