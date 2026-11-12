pub const MAX_HEADER: usize = 200;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ByteRange {
    Whole,
    Part { start: u64, end: u64 },
    Unsatisfiable,
}

fn number(text: &str) -> Option<u64> {
    if text.is_empty() || text.len() > 19 || !text.bytes().all(|b| b.is_ascii_digit()) {
        return None;
    }
    text.parse().ok()
}

#[must_use]
pub fn parse_range(header: &str, total: u64) -> ByteRange {
    let header = header.trim();
    if header.is_empty() {
        return ByteRange::Whole;
    }
    if header.len() > MAX_HEADER || total == 0 {
        return ByteRange::Unsatisfiable;
    }
    let Some(spec) = header.strip_prefix("bytes=") else {
        return ByteRange::Unsatisfiable;
    };
    let spec = spec.trim();
    if spec.contains(',') {
        return ByteRange::Unsatisfiable;
    }
    let Some((left, right)) = spec.split_once('-') else {
        return ByteRange::Unsatisfiable;
    };
    let last = total.saturating_sub(1);
    match (left.trim(), right.trim()) {
        ("", suffix) => match number(suffix) {
            Some(n) if n > 0 => ByteRange::Part {
                start: total.saturating_sub(n),
                end: last,
            },
            _ => ByteRange::Unsatisfiable,
        },
        (start, "") => match number(start) {
            Some(s) if s <= last => ByteRange::Part {
                start: s,
                end: last,
            },
            _ => ByteRange::Unsatisfiable,
        },
        (start, end) => match (number(start), number(end)) {
            (Some(s), Some(e)) if s <= e && s <= last => ByteRange::Part {
                start: s,
                end: e.min(last),
            },
            _ => ByteRange::Unsatisfiable,
        },
    }
}
