#![forbid(unsafe_code)]

mod home;
mod levels;
mod policy;
mod tools;

pub use home::{CRITICAL_CAP, HomeRules, HomeTables, MAX_TARGETS, MAX_TEXT, Target};
pub use levels::{Risk, Strength};
pub use policy::{Decision, Policy, Verdict};
pub use tools::{MAX_STEPS, MAX_TOOLS, RiskTable};

#[cfg(test)]
mod home_tests;
#[cfg(test)]
mod tests;
