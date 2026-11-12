#![forbid(unsafe_code)]

mod error;
mod fernet;

pub use error::{SealError, SealResult};
pub use fernet::{Fernet, MAX_CLOCK_SKEW, MAX_PLAINTEXT, generate_key};

#[cfg(test)]
mod tests;
