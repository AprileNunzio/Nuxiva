use unicode_normalization::UnicodeNormalization;

use crate::text::{is_py_space, py_strip};

pub const DEFAULT_NAME: &str = "Nuxiva";
pub const MAX_NAME_LENGTH: usize = 32;
const WAKE_PREFIXES: [&str; 8] = ["hey", "hei", "ehi", "hi", "ok", "okay", "oye", "hé"];

fn strip_wake_prefix(text: &str) -> &str {
    for prefix in WAKE_PREFIXES {
        let head: String = text.chars().take(prefix.chars().count()).collect();
        if head.to_lowercase() != prefix {
            continue;
        }
        let rest = text.get(head.len()..).unwrap_or_default();
        let trimmed = rest.trim_start_matches(is_py_space);
        if trimmed.len() < rest.len() {
            return trimmed;
        }
    }
    text
}

fn allowed(c: char) -> bool {
    c.is_alphanumeric() || c == '_' || is_py_space(c) || matches!(c, '\'' | '\u{2019}' | '.' | '-')
}

fn is_cased_upper(text: &str) -> bool {
    let mut cased = false;
    for c in text.chars() {
        if c.is_lowercase() {
            return false;
        }
        if c.is_uppercase() {
            cased = true;
        }
    }
    cased
}

fn capitalize(text: &str) -> String {
    let mut chars = text.chars();
    let Some(first) = chars.next() else {
        return String::new();
    };
    let mut out: String = first.to_uppercase().collect();
    out.extend(chars.flat_map(char::to_lowercase));
    out
}

#[must_use]
pub fn normalize_name(raw: &str) -> String {
    let text: String = raw.nfkc().collect();
    let stripped = strip_wake_prefix(py_strip(&text));
    let filtered: String = stripped.chars().filter(|c| allowed(*c)).collect();
    let collapsed = py_strip(&filtered)
        .split(is_py_space)
        .filter(|part| !part.is_empty())
        .collect::<Vec<_>>()
        .join(" ");
    let cut: String = collapsed.chars().take(MAX_NAME_LENGTH).collect();
    let name = py_strip(&cut);
    if name.is_empty() {
        return DEFAULT_NAME.to_owned();
    }
    if name.chars().count() > 1 && is_cased_upper(name) {
        capitalize(name)
    } else {
        name.to_owned()
    }
}
