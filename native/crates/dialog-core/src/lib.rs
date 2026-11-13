#![forbid(unsafe_code)]

mod addressee;
mod gate;
mod gate_seeds;
mod memory;

pub use addressee::{AddresseeRules, Context, Judgement, MAX_TEXT};
pub use gate::{DIM as GATE_DIM, GateVerdict, Intent, IntentGate, MAX_GATE_TEXT, embed};
pub use memory::{DialogueBook, KEEP, MAX_DEVICE, MAX_DEVICES, STALE_S, Turn, Windows};

#[cfg(test)]
mod gate_tests;
#[cfg(test)]
mod memory_tests;
#[cfg(test)]
mod tests;
