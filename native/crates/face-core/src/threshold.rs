use crate::vector::{leave_one_out, mean_std, percentile};

pub const MIN_FOR_STATS: usize = 6;
pub const FLOOR_DELTA: f32 = 0.08;
pub const GENUINE_SLACK: f32 = 0.06;
pub const GENUINE_PERCENTILE: f32 = 0.10;

#[must_use]
pub fn person_threshold(rows: &[Vec<f32>], dim: usize, base: f32) -> f32 {
    if rows.len() < MIN_FOR_STATS {
        return base;
    }
    let genuine = leave_one_out(rows, dim);
    percentile(&genuine, GENUINE_PERCENTILE).map_or(base, |low| {
        (low - GENUINE_SLACK).clamp(base - FLOOR_DELTA, base)
    })
}

#[must_use]
pub fn spread(rows: &[Vec<f32>], dim: usize) -> Option<f32> {
    if rows.len() < MIN_FOR_STATS {
        return None;
    }
    mean_std(&leave_one_out(rows, dim)).map(|(_, s)| s)
}
