#![forbid(unsafe_code)]

mod codec;
mod error;

pub use codec::{
    MAX_CLAIMS, MAX_SUBJECT, MAX_TOKEN, MAX_TTL, MIN_SECRET, PREFIX, Payload, SKEW, TokenCodec,
};
pub use error::{TokenError, TokenResult};

#[cfg(test)]
mod codec_tests;
