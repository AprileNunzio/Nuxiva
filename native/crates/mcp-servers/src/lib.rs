#![forbid(unsafe_code)]

mod build;
mod fs;

pub use build::{ServerDefinition, register_all};
pub use fs::{FileServer, FsConfig, Mode, RootConfig};

#[cfg(test)]
mod tests;
