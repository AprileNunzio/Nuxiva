use sha2::{Digest, Sha256};

use crate::error::{McpError, McpResult};

const SERVER_MAX: usize = 32;
const SUFFIX_LEN: usize = 9;

#[must_use]
pub fn valid_server_id(id: &str) -> bool {
    let mut chars = id.chars();
    let first_ok = chars
        .next()
        .is_some_and(|c| c.is_ascii_lowercase() || c.is_ascii_digit());
    first_ok
        && id.len() <= SERVER_MAX
        && chars.all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '_' || c == '-')
}

fn slug(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    let mut pending = false;
    for c in text.chars() {
        if c.is_ascii_alphanumeric() {
            if pending && !out.is_empty() {
                out.push('_');
            }
            pending = false;
            out.push(c.to_ascii_lowercase());
        } else {
            pending = true;
        }
    }
    out
}

fn tag(text: &str) -> String {
    Sha256::digest(text.as_bytes())
        .iter()
        .take(4)
        .flat_map(|b| [b >> 4, b & 15])
        .filter_map(|n| char::from_digit(u32::from(n), 16))
        .collect()
}

pub fn canonical_name(server_id: &str, remote: &str, max_len: usize) -> McpResult<String> {
    if !valid_server_id(server_id) || max_len <= SUFFIX_LEN {
        return Err(McpError::InvalidName);
    }
    let body = slug(remote);
    if body.is_empty() {
        return Err(McpError::InvalidName);
    }
    let base = format!("{server_id}.{body}");
    if base.len() <= max_len {
        return Ok(base);
    }
    let keep = max_len.saturating_sub(SUFFIX_LEN);
    let head: String = base.chars().take(keep).collect();
    Ok(format!(
        "{head}_{}",
        tag(&format!("{server_id}\u{0}{remote}"))
    ))
}
