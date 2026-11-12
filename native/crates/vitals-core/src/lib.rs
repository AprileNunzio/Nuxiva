#![forbid(unsafe_code)]

pub mod ble_heart_rate;
pub mod pulse;
pub mod watch;

#[cfg(test)]
mod tests;

pub use ble_heart_rate::{HeartRateSample, MAX_FRAME_BYTES, parse_heart_rate_measurement};
pub use pulse::{Estimate, agreed, breath_rate, heart_rate};
pub use watch::{Outcome, Seen, Shown, Source, Values, Watch, camera_allowed, valid_slug};
