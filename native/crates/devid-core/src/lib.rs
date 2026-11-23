pub mod mac;
pub mod resolve;

pub use mac::{normalize_mac, randomized};
pub use resolve::{Known, Resolution, Seen, resolve};

pub const MAX_KNOWN: usize = 20_000;
pub const SELF_KEY: &str = "self";

#[cfg(test)]
mod tests;
