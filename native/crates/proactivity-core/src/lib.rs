#![forbid(unsafe_code)]

mod actions;
mod clock;
mod engine;
mod error;
mod evaluate;
mod gate;
mod habit;
mod learn;
mod model;
mod rules;
mod settings;
mod state;

pub use clock::{Local, local};
pub use engine::Engine;
pub use error::{ProactivityError, ProactivityResult};
pub use gate::PersonPolicy;
pub use model::{
    Context, Decision, Domain, Explanation, Forecast, Level, Mode, Privacy, Reason, Signal,
    Situation, Stats, Urgency,
};
pub use rules::{ActionSpec, Audience, Cmp, Condition, HabitSpec, Rule, Ruleset, Undo, Window};
pub use settings::{MAX_PAYLOAD, Settings};

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::arithmetic_side_effects,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::field_reassign_with_default,
    clippy::cast_possible_truncation
)]
mod tests;
