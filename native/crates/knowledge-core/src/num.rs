pub const PERMILLE: u32 = 1000;

#[must_use]
pub fn clamp(value: u32) -> u32 {
    value.min(PERMILLE)
}

#[must_use]
pub fn noisy_or(a: u32, b: u32) -> u32 {
    let miss_a = PERMILLE.saturating_sub(clamp(a));
    let miss_b = PERMILLE.saturating_sub(clamp(b));
    PERMILLE.saturating_sub(
        miss_a
            .saturating_mul(miss_b)
            .checked_div(PERMILLE)
            .unwrap_or(0),
    )
}

#[must_use]
pub fn scale(value: u32, factor: u32) -> u32 {
    value
        .saturating_mul(factor)
        .checked_div(PERMILLE)
        .unwrap_or(0)
}

const PPM: i128 = 1_000_000;

fn pow2_neg_ppm(x_ppm: u64) -> u64 {
    let x = i128::from(x_ppm);
    let x2 = x.saturating_mul(x) / PPM;
    let x3 = x2.saturating_mul(x) / PPM;
    let x4 = x3.saturating_mul(x) / PPM;
    let x5 = x4.saturating_mul(x) / PPM;
    let plus = PPM
        .saturating_add(240_227_i128.saturating_mul(x2) / PPM)
        .saturating_add(9_618_i128.saturating_mul(x4) / PPM);
    let minus = 693_147_i128
        .saturating_mul(x)
        .saturating_add(55_504_i128.saturating_mul(x3))
        .saturating_add(1_333_i128.saturating_mul(x5))
        / PPM;
    u64::try_from(plus.saturating_sub(minus).clamp(0, PPM)).unwrap_or(0)
}

#[must_use]
pub fn halve(value: u32, elapsed_ms: u64, half_ms: u64) -> u32 {
    let Some(whole) = elapsed_ms.checked_div(half_ms) else {
        return value;
    };
    let rem = elapsed_ms.checked_rem(half_ms).unwrap_or(0);
    let shift = u32::try_from(whole.min(31)).unwrap_or(31);
    let base = u64::from(value.checked_shr(shift).unwrap_or(0));
    let x_ppm = u64::try_from(
        u128::from(rem)
            .saturating_mul(1_000_000)
            .checked_div(u128::from(half_ms))
            .unwrap_or(0),
    )
    .unwrap_or(0);
    let scaled = base
        .saturating_mul(pow2_neg_ppm(x_ppm))
        .checked_div(1_000_000)
        .unwrap_or(0);
    u32::try_from(scaled).unwrap_or(0)
}

#[must_use]
pub fn to_u16(value: u32) -> u16 {
    u16::try_from(clamp(value)).unwrap_or(1000)
}
