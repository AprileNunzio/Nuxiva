pub const DAY_MS: u64 = 86_400_000;
pub const HOUR_MS: u64 = 3_600_000;
pub const MINUTE_MS: u64 = 60_000;
pub const MAX_OFFSET_MIN: i32 = 840;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Local {
    pub day: u64,
    pub weekday: usize,
    pub minute: u32,
}

#[must_use]
pub fn local(now: u64, offset_min: i32) -> Local {
    let offset = i64::from(offset_min.clamp(-MAX_OFFSET_MIN, MAX_OFFSET_MIN));
    let shifted = i64::try_from(now)
        .unwrap_or(i64::MAX)
        .saturating_add(offset.saturating_mul(60_000))
        .max(0);
    let shifted = u64::try_from(shifted).unwrap_or(0);
    let day = shifted / DAY_MS;
    let weekday = usize::try_from(day.saturating_add(3) % 7).unwrap_or(0);
    let minute = u32::try_from((shifted % DAY_MS) / MINUTE_MS).unwrap_or(0);
    Local {
        day,
        weekday,
        minute,
    }
}

#[must_use]
pub fn in_span(minute: u32, start: u32, end: u32) -> bool {
    match start.cmp(&end) {
        std::cmp::Ordering::Equal => false,
        std::cmp::Ordering::Less => minute >= start && minute < end,
        std::cmp::Ordering::Greater => minute >= start || minute < end,
    }
}
