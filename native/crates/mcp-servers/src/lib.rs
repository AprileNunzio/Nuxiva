#![forbid(unsafe_code)]

mod build;
mod fetch;
mod fs;

pub use build::{ServerDefinition, register_all};
pub use fetch::{FetchConfig, FetchServer};
pub use fs::{FileServer, FsConfig, Mode, RootConfig};

#[cfg(test)]
mod tests;
