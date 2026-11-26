#![forbid(unsafe_code)]

mod capability;
mod client;
mod endpoint;
mod error;
mod media;
mod precision;
mod reply;
mod request;
mod sanitize;
mod secret;

pub use capability::{Capabilities, Capability, MAX_SCHEMA_BYTES};
pub use client::{Limits, StudioClient};
pub use endpoint::Endpoint;
pub use error::{StudioError, StudioResult};
pub use media::{Media, MediaKind, sniff};
pub use precision::{Precision, parse_precision};
pub use reply::{ChatReply, ModelInfo, Usage};
pub use request::{
    ChatRequest, ImageRequest, ImageSize, Message, Role, SpeechFormat, SpeechRequest,
};
pub use sanitize::{MAX_PROMPT_CHARS, clean_text, valid_id};
pub use secret::ApiKey;

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects
)]
mod tests;

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects
)]
mod http_tests;
