use std::sync::LazyLock;

use regex::{Captures, Regex, RegexBuilder};

pub const MASK: &str = "[oscurato]";

pub const KEEP_PREFIX: &[&str] = &[
    r"(?i)(bearer[ \t]+)[A-Za-z0-9._~+/=-]{8,}",
    r#"(?i)((?:password|passwd|pwd|passphrase|parola[ _-]?d'ordine|chiave|secret|token|api[_-]?key|access[_-]?key|client[_-]?secret|authorization|pin|otp)["']?[ \t]*[:=][ \t]*["']?)[^ \t\r\n"',;]+"#,
];

pub const WHOLE: &[&str] = &[
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
    r"sk-[A-Za-z0-9_-]{16,}",
    r"gh[pousr]_[A-Za-z0-9]{20,}",
    r"AKIA[0-9A-Z]{16}",
    r"xox[abposr]-[A-Za-z0-9-]{10,}",
    r"AIza[0-9A-Za-z_-]{35}",
    r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}",
    r"[A-Z]{2}[0-9]{2}(?:[ ]?[A-Z0-9]{4}){3,7}(?:[ ]?[A-Z0-9]{1,4})?",
    r"(?i)[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]",
];

pub const CARD: &str = r"[0-9](?:[ -]?[0-9]){12,18}";

fn build(pattern: &str) -> Option<Regex> {
    RegexBuilder::new(pattern).size_limit(1 << 22).build().ok()
}

static PREFIXED: LazyLock<Vec<Regex>> =
    LazyLock::new(|| KEEP_PREFIX.iter().filter_map(|p| build(p)).collect());
static WHOLES: LazyLock<Vec<Regex>> =
    LazyLock::new(|| WHOLE.iter().filter_map(|p| build(p)).collect());
static CARDS: LazyLock<Option<Regex>> = LazyLock::new(|| build(CARD));

#[must_use]
pub fn luhn(digits: &str) -> bool {
    let mut sum = 0u32;
    let mut count = 0u32;
    for (i, c) in digits
        .chars()
        .rev()
        .filter(char::is_ascii_digit)
        .enumerate()
    {
        let Some(mut d) = c.to_digit(10) else {
            return false;
        };
        if i % 2 == 1 {
            d = d.saturating_mul(2);
            if d > 9 {
                d = d.saturating_sub(9);
            }
        }
        sum = sum.saturating_add(d);
        count = count.saturating_add(1);
    }
    (13..=19).contains(&count) && sum % 10 == 0
}

#[must_use]
pub fn redact(text: &str) -> String {
    let mut out = text.to_owned();
    for re in WHOLES.iter() {
        out = re.replace_all(&out, MASK).into_owned();
    }
    for re in PREFIXED.iter() {
        out = re
            .replace_all(&out, |c: &Captures<'_>| {
                format!("{}{MASK}", c.get(1).map_or("", |m| m.as_str()))
            })
            .into_owned();
    }
    if let Some(re) = CARDS.as_ref() {
        out = re
            .replace_all(&out, |c: &Captures<'_>| {
                let found = c.get(0).map_or("", |m| m.as_str());
                if luhn(found) {
                    MASK.to_owned()
                } else {
                    found.to_owned()
                }
            })
            .into_owned();
    }
    out
}

#[must_use]
pub fn patterns() -> (Vec<&'static str>, Vec<&'static str>, &'static str) {
    (KEEP_PREFIX.to_vec(), WHOLE.to_vec(), CARD)
}
