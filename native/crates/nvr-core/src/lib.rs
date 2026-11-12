#![forbid(unsafe_code)]

pub mod catalog;
pub mod error;
pub mod range;
pub mod retention;
pub mod segment;
pub mod timeline;

#[cfg(test)]
mod tests;

pub use catalog::{Catalog, Seek};
pub use error::{NvrError, NvrResult};
pub use range::{ByteRange, parse_range};
pub use retention::{Policy, RetentionPlan, plan};
pub use segment::{Segment, Tier, valid_id};
pub use timeline::{Marker, Span, next_marker, spans};
