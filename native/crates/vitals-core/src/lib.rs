#![forbid(unsafe_code)]

pub mod ble_heart_rate;

pub use ble_heart_rate::{HeartRateSample, MAX_FRAME_BYTES, parse_heart_rate_measurement};
