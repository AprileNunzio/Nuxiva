use crate::error::{GraphError, GraphResult};

pub fn validate(path: &str, max_chars: usize) -> GraphResult<()> {
    let ok = !path.is_empty()
        && path.chars().count() <= max_chars
        && !path.starts_with('/')
        && !path.contains('\\')
        && !path.chars().any(char::is_control)
        && path
            .split('/')
            .all(|part| !part.is_empty() && part != "." && part != "..");
    if ok { Ok(()) } else { Err(GraphError::Path) }
}

#[must_use]
pub fn parent(path: &str) -> &str {
    path.rsplit_once('/').map_or("", |(dir, _)| dir)
}

#[must_use]
pub fn file_name(path: &str) -> &str {
    path.rsplit_once('/').map_or(path, |(_, name)| name)
}

#[must_use]
pub fn stem(path: &str) -> &str {
    let name = file_name(path);
    name.rsplit_once('.').map_or(name, |(stem, _)| stem)
}

#[must_use]
pub fn join(dir: &str, rel: &str) -> Option<String> {
    let mut parts: Vec<&str> = if dir.is_empty() {
        Vec::new()
    } else {
        dir.split('/').collect()
    };
    for piece in rel.split('/') {
        match piece {
            "" | "." => {}
            ".." => {
                parts.pop()?;
            }
            other => parts.push(other),
        }
    }
    if parts.is_empty() {
        None
    } else {
        Some(parts.join("/"))
    }
}
