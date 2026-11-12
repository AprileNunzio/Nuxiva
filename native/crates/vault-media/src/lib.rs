#![forbid(unsafe_code)]
#![allow(
    clippy::cast_precision_loss,
    clippy::cast_possible_truncation,
    clippy::cast_sign_loss
)]

pub mod crypto;
pub mod error;
pub mod retention;
pub mod segment;
pub mod stream;
pub mod v2;

#[cfg(test)]
mod tests;
#[cfg(test)]
mod v2_tests;

pub use crypto::{
    CHUNK_SIZE, KEY_LEN, NONCE_LEN, decrypt_chunk, derive_day_camera_key, derive_segment_key,
    encrypt_chunk,
};
pub use error::{MediaVaultError, MediaVaultResult};
pub use retention::{RetentionPolicy, RetentionTier};
pub use segment::{EncryptedSegment, RawSegmentInput, SegmentMeta};
pub use stream::DecryptingStreamReader;
