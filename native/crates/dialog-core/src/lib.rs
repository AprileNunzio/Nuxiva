#![forbid(unsafe_code)]

mod addressee;
mod memory;

pub use addressee::{AddresseeRules, Context, Judgement, MAX_TEXT};
pub use memory::{DialogueBook, KEEP, MAX_DEVICE, MAX_DEVICES, STALE_S, Turn, Windows};

#[cfg(test)]
mod memory_tests;
#[cfg(test)]
mod tests;
