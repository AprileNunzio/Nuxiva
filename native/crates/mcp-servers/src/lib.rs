#![forbid(unsafe_code)]

mod build;
mod fetch;
mod fs;
mod mirror;

pub use build::{ServerDefinition, register_all};
pub use fetch::{FetchConfig, FetchServer};
pub use fs::{FileServer, FsConfig, Mode, RootConfig};
pub use mirror::{Dispatch, MirrorConfig, MirrorServer, MirrorTool};

#[cfg(test)]
mod tests;
