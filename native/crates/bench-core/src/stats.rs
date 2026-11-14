use serde::{Deserialize, Serialize};

use crate::error::{BenchError, BenchResult};

const TWO_POW_32: u64 = 4_294_967_296;

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Summary {
    pub n: u64,
    pub mean: f64,
    pub p50: f64,
    pub p95: f64,
    pub p99: f64,
    pub max: f64,
}

#[must_use]
pub fn u64_f64(n: u64) -> f64 {
    let high = u32::try_from(n / TWO_POW_32).unwrap_or(u32::MAX);
    let low = u32::try_from(n % TWO_POW_32).unwrap_or(u32::MAX);
    f64::from(high) * 4_294_967_296.0 + f64::from(low)
}

#[must_use]
pub fn count_f(n: usize) -> f64 {
    u64_f64(u64::try_from(n).unwrap_or(u64::MAX))
}

#[must_use]
pub fn ratio(numerator: u64, denominator: u64) -> f64 {
    if denominator == 0 {
        0.0
    } else {
        round6(u64_f64(numerator) / u64_f64(denominator))
    }
}

#[must_use]
pub fn round3(value: f64) -> f64 {
    (value * 1_000.0).round() / 1_000.0
}

#[must_use]
pub fn round6(value: f64) -> f64 {
    (value * 1_000_000.0).round() / 1_000_000.0
}

fn pick(sorted: &[f64], pct: usize) -> f64 {
    let rank = sorted.len().saturating_mul(pct).div_ceil(100).max(1);
    sorted
        .get(rank.saturating_sub(1))
        .copied()
        .unwrap_or_default()
}

pub fn summarize(values: &[f64]) -> BenchResult<Summary> {
    if values.is_empty() {
        return Ok(Summary::default());
    }
    if values.iter().any(|v| !v.is_finite() || *v < 0.0) {
        return Err(BenchError::Invalid("sample"));
    }
    let mut sorted = values.to_vec();
    sorted.sort_by(f64::total_cmp);
    let sum: f64 = sorted.iter().sum();
    Ok(Summary {
        n: u64::try_from(sorted.len()).unwrap_or(u64::MAX),
        mean: round3(sum / count_f(sorted.len())),
        p50: round3(pick(&sorted, 50)),
        p95: round3(pick(&sorted, 95)),
        p99: round3(pick(&sorted, 99)),
        max: round3(sorted.last().copied().unwrap_or_default()),
    })
}
