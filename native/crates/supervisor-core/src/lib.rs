#![forbid(unsafe_code)]

mod book;
mod model;

pub use book::{LoopBook, MAX_LOOPS, MAX_NAME, MAX_REASON};
pub use model::{Action, Decision, LoopState, LoopView, Outcome, Policy, Totals};

#[cfg(test)]
mod tests;
