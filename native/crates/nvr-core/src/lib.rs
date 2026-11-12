#![forbid(unsafe_code)]

pub mod catalog;
pub mod error;
pub mod index;
pub mod policy;
pub mod range;
pub mod retention;
pub mod segment;
pub mod timeline;
pub mod transcript;
pub mod voices;

#[cfg(test)]
mod tests;

pub use catalog::{Catalog, Seek};
pub use error::{NvrError, NvrResult};
pub use index::{BlindIndex, DocMeta, Hit, tokens};
pub use policy::{AudioDecision, audio_decision, is_private_room};
pub use range::{ByteRange, parse_range};
pub use retention::{Policy, RetentionPlan, plan};
pub use segment::{Segment, Tier, valid_id};
pub use timeline::{Marker, Span, next_marker, spans};
pub use transcript::{Turn, Utterance, fuse};
pub use voices::cluster_voices;
