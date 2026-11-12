#![forbid(unsafe_code)]

pub mod checkpoint;
pub mod error;
pub mod event;
pub mod journal;
pub mod keys;
pub mod kind;
pub mod query;
pub mod retention;

pub use error::SentinelError;
pub use event::{Event, Narrative, Sensitivity, Subject};
pub use journal::{Day, Head};
pub use kind::{Group, Kind};
pub use query::Query;
pub use retention::Retention;

#[cfg(test)]
mod tests;
#[cfg(test)]
mod tests_crypto;
