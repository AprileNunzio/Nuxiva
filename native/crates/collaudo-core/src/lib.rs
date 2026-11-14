#![forbid(unsafe_code)]

mod envelope;
mod error;
mod hub;
mod redact;
mod report;
mod smoke;
mod store;
mod token;

pub use envelope::{Domain, Envelope, Level, RawEvent, SCHEMA, Scalar, is_hex, is_token};
pub use error::CollaudoError;
pub use hub::{Hub, Mode, Stats};
pub use redact::Redactor;
pub use report::{DomainStat, ErrorStat, Latency, Regression, Report, Verdict, analyze, compare};
pub use smoke::{Bound, Check, CheckResult, Rule, Severity, Status, default_spec, evaluate};
pub use store::{Integrity, Query, SegmentMeta, Store, StoreConfig};
pub use token::{TokenVault, generate, random_id, random_key};

#[cfg(test)]
mod tests;
