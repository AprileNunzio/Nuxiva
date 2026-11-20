pub mod error;
pub mod index;
pub mod quantize;
pub mod vector;

#[cfg(test)]
#[allow(clippy::unwrap_used, clippy::panic, clippy::indexing_slicing)]
mod tests;

pub use error::TernaryError;
pub use index::{TernaryIndex, TernaryRecord};
pub use quantize::quantize_dense;
pub use vector::TernaryVector;
