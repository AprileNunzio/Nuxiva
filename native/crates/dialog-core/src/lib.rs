#![forbid(unsafe_code)]

mod addressee;

pub use addressee::{AddresseeRules, Context, Judgement, MAX_TEXT};

#[cfg(test)]
mod tests;
