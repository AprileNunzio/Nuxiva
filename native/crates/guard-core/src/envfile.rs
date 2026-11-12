use crate::error::{GuardError, GuardResult};
use crate::text::{py_strip, split_lines};

pub type EnvEntry = (Option<String>, String);

fn valid_key(key: &str) -> bool {
    let mut bytes = key.bytes();
    bytes
        .next()
        .is_some_and(|b| b.is_ascii_alphabetic() || b == b'_')
        && bytes.all(|b| b.is_ascii_alphanumeric() || b == b'_')
}

fn unquote_json(value: &str) -> Option<String> {
    let inner = value.strip_prefix('"')?.strip_suffix('"')?;
    let mut out = String::with_capacity(inner.len());
    let mut chars = inner.chars();
    while let Some(c) = chars.next() {
        match c {
            '"' => return None,
            c if u32::from(c) < 0x20 => return None,
            '\\' => match chars.next()? {
                '"' => out.push('"'),
                '\\' => out.push('\\'),
                '/' => out.push('/'),
                'b' => out.push('\u{8}'),
                'f' => out.push('\u{c}'),
                'n' => out.push('\n'),
                'r' => out.push('\r'),
                't' => out.push('\t'),
                'u' => out.push(unicode_escape(&mut chars)?),
                _ => return None,
            },
            c => out.push(c),
        }
    }
    Some(out)
}

fn hex4(chars: &mut std::str::Chars<'_>) -> Option<u32> {
    let mut value = 0u32;
    for _ in 0..4 {
        let digit = chars.next()?.to_digit(16)?;
        value = value.checked_mul(16)?.checked_add(digit)?;
    }
    Some(value)
}

fn unicode_escape(chars: &mut std::str::Chars<'_>) -> Option<char> {
    let first = hex4(chars)?;
    if (0xD800..0xDC00).contains(&first) {
        let mut look = chars.clone();
        if look.next()? != '\\' || look.next()? != 'u' {
            return None;
        }
        let second = hex4(&mut look)?;
        if !(0xDC00..0xE000).contains(&second) {
            return None;
        }
        *chars = look;
        let high = first.checked_sub(0xD800)?.checked_mul(0x400)?;
        let low = second.checked_sub(0xDC00)?;
        return char::from_u32(high.checked_add(low)?.checked_add(0x10000)?);
    }
    char::from_u32(first)
}

#[must_use]
pub fn decode_value(value: &str) -> String {
    let mut current = py_strip(value).to_owned();
    loop {
        let bytes = current.as_bytes();
        let (Some(first), Some(last)) = (bytes.first(), bytes.last()) else {
            return current;
        };
        if current.chars().count() < 2 || first != last || !matches!(first, b'"' | b'\'') {
            return current;
        }
        if *first == b'"' {
            if let Some(decoded) = unquote_json(&current.replace("\\$", "$")) {
                return decoded;
            }
        }
        let inner = current
            .get(1..current.len().saturating_sub(1))
            .unwrap_or_default();
        let next = py_strip(inner).to_owned();
        current = next;
    }
}

fn push_control(out: &mut String, c: char) {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    out.push_str("\\u00");
    let code = u32::from(c);
    for nibble in [code >> 4, code & 0x0f] {
        let index = usize::try_from(nibble).unwrap_or_default();
        out.push(HEX.get(index).map_or('0', |b| char::from(*b)));
    }
}

fn encode_json(value: &str) -> String {
    let mut out = String::with_capacity(value.len().saturating_add(2));
    out.push('"');
    for c in value.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{8}' => out.push_str("\\b"),
            '\u{c}' => out.push_str("\\f"),
            '$' => out.push_str("\\$"),
            c if u32::from(c) < 0x20 => push_control(&mut out, c),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

pub fn format_line(key: &str, value: &str) -> GuardResult<String> {
    if !valid_key(key) {
        return Err(GuardError::EnvKey);
    }
    if value.contains(['\n', '\r', '\0']) {
        return Err(GuardError::EnvValue);
    }
    Ok(format!("{key}={}", encode_json(value)))
}

#[must_use]
pub fn entries(text: &str) -> Vec<EnvEntry> {
    let mut seen = std::collections::HashSet::new();
    let mut out = Vec::new();
    for raw in split_lines(text) {
        let line = py_strip(raw);
        if line.starts_with('#') {
            out.push((None, line.to_owned()));
        } else if let Some((key, value)) = line.split_once('=') {
            let key = py_strip(py_strip(key).trim_matches(['"', '\'']));
            if valid_key(key) && seen.insert(key.to_owned()) {
                out.push((Some(key.to_owned()), decode_value(value)));
            }
        }
    }
    out
}

pub fn normalize(text: &str) -> GuardResult<String> {
    let mut lines = Vec::new();
    for (key, value) in entries(text) {
        lines.push(match key {
            None => value,
            Some(key) => format_line(&key, &value)?,
        });
    }
    let mut out = lines.join("\n");
    out.push('\n');
    Ok(out)
}
