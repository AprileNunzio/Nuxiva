#![forbid(unsafe_code)]

pub mod audience;
pub mod error;
pub mod section;
pub mod sensitivity;

pub use audience::AudienceKind;
pub use error::DomainError;
pub use section::{SectionKey, Version};
pub use sensitivity::Sensitivity;

#[cfg(test)]
mod tests;
