#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Stamp {
    pub year: u64,
    pub month: u64,
    pub day: u64,
    pub hour: u64,
    pub minute: u64,
    pub second: u64,
}

#[must_use]
pub fn stamp(ms: u64) -> Stamp {
    let secs = ms / 1000;
    let days = secs / 86_400;
    let rem = secs % 86_400;
    let z = days.saturating_add(719_468);
    let era = z / 146_097;
    let doe = z.saturating_sub(era.saturating_mul(146_097));
    let yoe = doe
        .saturating_sub(doe / 1460)
        .saturating_add(doe / 36_524)
        .saturating_sub(doe / 146_096)
        / 365;
    let doy = doe.saturating_sub(
        yoe.saturating_mul(365)
            .saturating_add(yoe / 4)
            .saturating_sub(yoe / 100),
    );
    let mp = doy.saturating_mul(5).saturating_add(2) / 153;
    let day = doy
        .saturating_sub(mp.saturating_mul(153).saturating_add(2) / 5)
        .saturating_add(1);
    let month = if mp < 10 {
        mp.saturating_add(3)
    } else {
        mp.saturating_sub(9)
    };
    let year = yoe
        .saturating_add(era.saturating_mul(400))
        .saturating_add(u64::from(month <= 2));
    Stamp {
        year,
        month,
        day,
        hour: rem / 3600,
        minute: rem % 3600 / 60,
        second: rem % 60,
    }
}

#[must_use]
pub fn iso(ms: u64) -> String {
    let s = stamp(ms);
    format!(
        "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}Z",
        s.year, s.month, s.day, s.hour, s.minute, s.second
    )
}

#[must_use]
pub fn day_path(ms: u64) -> String {
    let s = stamp(ms);
    format!("{:04}/{:02}/{:02}", s.year, s.month, s.day)
}

#[must_use]
pub fn operation_id(ms: u64, suffix: [u8; 3]) -> String {
    let s = stamp(ms);
    format!(
        "{:04}{:02}{:02}-{:02}{:02}{:02}-{:02x}{:02x}{:02x}",
        s.year, s.month, s.day, s.hour, s.minute, s.second, suffix[0], suffix[1], suffix[2]
    )
}
