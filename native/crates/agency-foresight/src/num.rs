pub fn count(value: usize) -> f64 {
    f64::from(u32::try_from(value).unwrap_or(u32::MAX))
}

pub fn mean(sum: f64, items: usize) -> f64 {
    if items == 0 { 0.0 } else { sum / count(items) }
}

pub fn round3(value: f64) -> f64 {
    (value * 1_000.0).round() / 1_000.0
}
