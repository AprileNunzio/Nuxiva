#![forbid(unsafe_code)]

mod bridge;
mod error;
mod learn;
mod ledger;
mod reward;
mod signal;

pub use bridge::{from_report, from_verdict, task_of};
pub use error::{RewardError, RewardResult};
pub use learn::{
    Adjustment, Learner, MAX_STEP_BPS, MIN_CHANGE_BPS, MIN_TRIALS, UNSAFE_PER_MILLE, apply,
};
pub use ledger::{Key, Ledger, MAX_KEYS, MAX_LEDGER_BYTES, Subject, Tally, WINDOW};
pub use reward::{GAIN_MAX, Reward, SCORE_MAX, SCORE_MIN, score};
pub use signal::{Signal, StepOutcome};

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects
)]
mod tests;
