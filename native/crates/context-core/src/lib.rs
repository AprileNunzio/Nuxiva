#![forbid(unsafe_code)]

mod delta;
mod error;
mod id;
mod lexicon;
mod model;
mod policy;
mod profile;
mod render;
mod seal;
mod settings;
mod shared;
mod snapshot;

pub use delta::Delta;
pub use error::{ContextError, ContextResult};
pub use id::PersonId;
pub use lexicon::{Labels, Lang};
pub use model::{Affect, Custom, Listen, Person, Prefs, Relation, Role};
pub use policy::{Audience, FieldKey, Policy};
pub use profile::person_from_profile;
pub use render::Request;
pub use seal::{Sealed, Sealer, Vitals};
pub use settings::ContextSettings;
pub use shared::SharedContext;
pub use snapshot::Snapshot;

#[cfg(test)]
mod tests;
#[cfg(test)]
mod tests_bench;
#[cfg(test)]
mod tests_concurrency;
#[cfg(test)]
mod tests_profile;
