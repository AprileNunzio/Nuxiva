const MAX_HOST: usize = 40;
const SUFFIX: &str = ".png";

#[must_use]
pub fn host_label(raw: &str) -> String {
    let mut out = String::new();
    for c in raw.chars() {
        let c = c.to_ascii_lowercase();
        if c.is_ascii_alphanumeric() {
            out.push(c);
        } else if matches!(c, '-' | '_' | '.' | ' ') && !out.ends_with('-') && !out.is_empty() {
            out.push('-');
        }
        if out.len() >= MAX_HOST {
            break;
        }
    }
    let trimmed = out.trim_matches('-').to_owned();
    if trimmed.is_empty() {
        "nodo".to_owned()
    } else {
        trimmed
    }
}

#[must_use]
pub fn civil(secs: u64) -> (u64, u64, u64, u64, u64, u64) {
    let days = secs / 86_400;
    let rem = secs % 86_400;
    let z = days.saturating_add(719_468);
    let era = z / 146_097;
    let doe = z % 146_097;
    let yoe = doe
        .saturating_sub(doe / 1460)
        .saturating_add(doe / 36_524)
        .saturating_sub(doe / 146_096)
        / 365;
    let doy = doe.saturating_sub(
        (365u64.saturating_mul(yoe))
            .saturating_add(yoe / 4)
            .saturating_sub(yoe / 100),
    );
    let mp = (5u64.saturating_mul(doy).saturating_add(2)) / 153;
    let day = doy
        .saturating_sub((153u64.saturating_mul(mp).saturating_add(2)) / 5)
        .saturating_add(1);
    let month = if mp < 10 {
        mp.saturating_add(3)
    } else {
        mp.saturating_sub(9)
    };
    let mut year = yoe.saturating_add(era.saturating_mul(400));
    if month <= 2 {
        year = year.saturating_add(1);
    }
    (year, month, day, rem / 3600, (rem % 3600) / 60, rem % 60)
}

#[must_use]
pub fn file_name(host: &str, secs: u64, seq: u32) -> String {
    let (y, mo, d, h, mi, s) = civil(secs);
    format!(
        "{}_{y:04}{mo:02}{d:02}-{h:02}{mi:02}{s:02}_{:03}{SUFFIX}",
        host_label(host),
        seq % 1000
    )
}

#[must_use]
pub fn is_managed(name: &str) -> bool {
    let Some(stem) = name.strip_suffix(SUFFIX) else {
        return false;
    };
    let mut parts = stem.rsplitn(3, '_');
    let (Some(seq), Some(stamp), Some(host)) = (parts.next(), parts.next(), parts.next()) else {
        return false;
    };
    let digits = |s: &str, n: usize| s.len() == n && s.bytes().all(|b| b.is_ascii_digit());
    let stamp_ok = stamp
        .split_once('-')
        .is_some_and(|(d, t)| digits(d, 8) && digits(t, 6));
    digits(seq, 3)
        && stamp_ok
        && !host.is_empty()
        && host.len() <= MAX_HOST
        && host
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-')
}

#[must_use]
pub fn stamp_secs(name: &str) -> Option<u64> {
    if !is_managed(name) {
        return None;
    }
    let stem = name.strip_suffix(SUFFIX)?;
    let mut parts = stem.rsplitn(3, '_');
    let _seq = parts.next()?;
    let stamp = parts.next()?;
    let (date, time) = stamp.split_once('-')?;
    let num = |s: &str| s.parse::<u64>().ok();
    let (y, mo, d) = (
        num(date.get(0..4)?)?,
        num(date.get(4..6)?)?,
        num(date.get(6..8)?)?,
    );
    let (h, mi, s) = (
        num(time.get(0..2)?)?,
        num(time.get(2..4)?)?,
        num(time.get(4..6)?)?,
    );
    if !(1..=12).contains(&mo) || !(1..=31).contains(&d) || h > 23 || mi > 59 || s > 60 {
        return None;
    }
    let y_adj = if mo <= 2 { y.checked_sub(1)? } else { y };
    let era = y_adj / 400;
    let yoe = y_adj % 400;
    let m_shift = if mo > 2 {
        mo.checked_sub(3)?
    } else {
        mo.saturating_add(9)
    };
    let doy = ((153u64.saturating_mul(m_shift).saturating_add(2)) / 5)
        .saturating_add(d.saturating_sub(1));
    let doe = yoe
        .saturating_mul(365)
        .saturating_add(yoe / 4)
        .saturating_sub(yoe / 100)
        .saturating_add(doy);
    let days = era
        .saturating_mul(146_097)
        .saturating_add(doe)
        .checked_sub(719_468)?;
    Some(
        days.saturating_mul(86_400).saturating_add(
            h.saturating_mul(3600)
                .saturating_add(mi.saturating_mul(60))
                .saturating_add(s),
        ),
    )
}
