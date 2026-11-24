use std::collections::BTreeSet;

use crate::error::{RouteError, RouteResult};

pub const MAX_PROMPT_BYTES: usize = 1024 * 1024;

#[must_use]
pub fn estimate_tokens(text: &str) -> u32 {
    u32::try_from(text.len().div_ceil(4)).unwrap_or(u32::MAX)
}

pub fn compact(sections: &[&str], budget_tokens: u32) -> RouteResult<String> {
    let total: usize = sections.iter().map(|s| s.len()).sum();
    if total > MAX_PROMPT_BYTES {
        return Err(RouteError::TooLarge);
    }
    let mut seen = BTreeSet::new();
    let mut out = String::new();
    for section in sections {
        let normalized: String = section.split_whitespace().collect::<Vec<_>>().join(" ");
        if normalized.is_empty() || !seen.insert(*blake3::hash(normalized.as_bytes()).as_bytes()) {
            continue;
        }
        let candidate_len = out.len().saturating_add(normalized.len()).saturating_add(1);
        if estimate_tokens(&" ".repeat(candidate_len)) > budget_tokens {
            break;
        }
        if !out.is_empty() {
            out.push('\n');
        }
        out.push_str(&normalized);
    }
    if out.is_empty() && sections.iter().any(|s| !s.trim().is_empty()) {
        return Err(RouteError::TooLarge);
    }
    Ok(out)
}
