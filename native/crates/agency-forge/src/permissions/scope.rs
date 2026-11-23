use crate::error::ForgeError;

const MAX_PATH_BYTES: usize = 256;
const MAX_HOST_BYTES: usize = 253;

fn invalid(reason: &str) -> ForgeError {
    ForgeError::InvalidPermissions(reason.to_owned())
}

pub fn normalize_path(raw: &str) -> Result<String, ForgeError> {
    let trimmed = raw.trim();
    if trimmed.is_empty() || trimmed.len() > MAX_PATH_BYTES {
        return Err(invalid("path length out of range"));
    }
    if trimmed.starts_with('/') || trimmed.contains('\\') || trimmed.contains('\0') {
        return Err(invalid("path must be relative and use forward slashes"));
    }
    let mut parts = Vec::new();
    for part in trimmed.split('/') {
        if part.is_empty() || part == "." || part == ".." || part.starts_with('.') {
            return Err(invalid("path segment not allowed"));
        }
        if part.chars().any(char::is_control) {
            return Err(invalid("path contains control characters"));
        }
        parts.push(part);
    }
    Ok(parts.join("/"))
}

pub fn normalize_host(raw: &str) -> Result<String, ForgeError> {
    let host = raw.trim().to_ascii_lowercase();
    if host.is_empty() || host.len() > MAX_HOST_BYTES {
        return Err(invalid("host length out of range"));
    }
    let valid_label = |label: &str| {
        !label.is_empty()
            && label.len() <= 63
            && !label.starts_with('-')
            && !label.ends_with('-')
            && label.chars().all(|c| c.is_ascii_alphanumeric() || c == '-')
    };
    if !host.split('.').all(valid_label) {
        return Err(invalid("host is not a valid hostname"));
    }
    Ok(host)
}
