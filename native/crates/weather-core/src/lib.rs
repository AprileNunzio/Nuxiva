pub mod insights;
pub mod verify;

pub use insights::{Insight, Level, Situation, insights};
pub use verify::{Forecast, ModelScore, Observation, Verdict, verify};

pub const MAX_ITEMS: usize = 20_000;

#[must_use]
pub fn round_to(value: f64, digits: i32) -> f64 {
    let scale = 10f64.powi(digits);
    (value * scale + 0.5).floor() / scale
}

#[cfg(test)]
mod tests;
