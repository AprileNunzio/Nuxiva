#[must_use]
#[allow(clippy::cast_precision_loss)]
pub fn as_f64(value: u64) -> f64 {
    value as f64
}

#[must_use]
pub fn percent(part: u64, whole: u64) -> f64 {
    if whole == 0 {
        return 0.0;
    }
    round_to(as_f64(part) / as_f64(whole) * 100.0, 1)
}

#[must_use]
pub fn round_to(value: f64, digits: i32) -> f64 {
    if !value.is_finite() {
        return 0.0;
    }
    let scale = 10f64.powi(digits);
    (value * scale).round() / scale
}

#[must_use]
#[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
pub fn to_u64(value: f64) -> u64 {
    if value.is_finite() && value > 0.0 {
        value as u64
    } else {
        0
    }
}
