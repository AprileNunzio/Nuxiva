use crate::error::{LoopError, LoopResult};

pub const MAX_PATH: usize = 240;

#[must_use]
pub fn prefix_ok(prefix: &str) -> bool {
    !prefix.is_empty() && prefix.ends_with('/') && normalize(prefix.trim_end_matches('/')).is_ok()
}

pub fn normalize(path: &str) -> LoopResult<String> {
    if path.is_empty()
        || path.len() > MAX_PATH
        || path.starts_with('/')
        || path.contains('\\')
        || path.chars().any(|c| c.is_control() || c == ':')
    {
        return Err(LoopError::Path);
    }
    let mut parts: Vec<&str> = Vec::new();
    for part in path.split('/') {
        match part {
            "" | "." | ".." => return Err(LoopError::Path),
            other => parts.push(other),
        }
    }
    Ok(parts.join("/").to_lowercase())
}

#[must_use]
pub fn is_protected(path: &str, prefixes: &[String]) -> bool {
    let lowered = path.to_lowercase();
    prefixes.iter().any(|p| {
        let p = p.to_lowercase();
        lowered.starts_with(&p) || format!("{lowered}/").starts_with(&p)
    })
}
