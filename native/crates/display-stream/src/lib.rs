#![forbid(unsafe_code)]

pub mod apply;
pub mod channel;
pub mod diff;
pub mod error;
pub mod op;
pub mod pointer;

pub use apply::apply;
pub use channel::{Channel, Frame};
pub use diff::diff;
pub use error::StreamError;
pub use op::Op;

#[cfg(test)]
mod tests;
