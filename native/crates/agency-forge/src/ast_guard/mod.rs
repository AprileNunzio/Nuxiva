use serde::{Deserialize, Serialize};

use crate::error::ForgeError;

pub const MAX_SOURCE_BYTES: usize = 8_000;
pub const MAX_SOURCE_LINES: usize = 160;

pub const ALLOWED_IMPORTS: [&str; 12] = [
    "collections",
    "datetime",
    "decimal",
    "fractions",
    "functools",
    "heapq",
    "itertools",
    "json",
    "math",
    "re",
    "statistics",
    "string",
];

const FORBIDDEN_PATTERNS: [&str; 18] = [
    "__import__",
    "__subclasses__",
    "__builtins__",
    "__globals__",
    "__code__",
    "__dict__",
    "__class__",
    "__bases__",
    "eval(",
    "exec(",
    "compile(",
    "open(",
    "getattr(",
    "setattr(",
    "delattr(",
    "globals(",
    "locals(",
    "breakpoint(",
];

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct GuardVerdict {
    pub allowed_imports_used: Vec<String>,
    pub line_count: usize,
    pub byte_len: usize,
}

pub fn validate_tool_name(raw: &str) -> Result<String, ForgeError> {
    let trimmed = raw.trim().trim_start_matches("x_");
    let len = trimmed.len();
    let valid_chars = trimmed
        .chars()
        .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '_');
    let starts_letter = trimmed
        .chars()
        .next()
        .is_some_and(|c| c.is_ascii_lowercase());
    if !(3..=40).contains(&len) || !valid_chars || !starts_letter {
        return Err(ForgeError::InvalidName(raw.to_owned()));
    }
    Ok(trimmed.to_owned())
}

fn check_imports(line: &str, used: &mut Vec<String>) -> Result<(), ForgeError> {
    let trimmed = line.trim();
    if let Some(rest) = trimmed.strip_prefix("import ") {
        for part in rest.split(',') {
            let module = part
                .split_whitespace()
                .next()
                .unwrap_or("")
                .split('.')
                .next()
                .unwrap_or("");
            if module.is_empty() || !ALLOWED_IMPORTS.contains(&module) {
                return Err(ForgeError::GuardRejected(format!(
                    "disallowed import '{module}'"
                )));
            }
            if !used.iter().any(|u| u == module) {
                used.push(module.to_owned());
            }
        }
    } else if let Some(rest) = trimmed.strip_prefix("from ") {
        let module = rest
            .split_whitespace()
            .next()
            .unwrap_or("")
            .split('.')
            .next()
            .unwrap_or("");
        if module.is_empty() || !ALLOWED_IMPORTS.contains(&module) {
            return Err(ForgeError::GuardRejected(format!(
                "disallowed from-import '{module}'"
            )));
        }
        if !used.iter().any(|u| u == module) {
            used.push(module.to_owned());
        }
    }
    Ok(())
}

pub fn inspect_tool_source(source: &str) -> Result<GuardVerdict, ForgeError> {
    let trimmed = source.trim();
    if trimmed.is_empty() {
        return Err(ForgeError::GuardRejected("empty source code".to_owned()));
    }
    if source.len() > MAX_SOURCE_BYTES {
        return Err(ForgeError::GuardRejected(format!(
            "source exceeds {MAX_SOURCE_BYTES} bytes"
        )));
    }
    let lines: Vec<&str> = source.lines().collect();
    if lines.len() > MAX_SOURCE_LINES {
        return Err(ForgeError::GuardRejected(format!(
            "source exceeds {MAX_SOURCE_LINES} lines"
        )));
    }

    let has_run_fn = lines.iter().any(|l| {
        let t = l.trim_start();
        t.starts_with("def run(")
    });
    if !has_run_fn {
        return Err(ForgeError::GuardRejected(
            "missing required 'def run(args):' entrypoint".to_owned(),
        ));
    }

    for pattern in FORBIDDEN_PATTERNS {
        if source.contains(pattern) {
            return Err(ForgeError::GuardRejected(format!(
                "forbidden construct '{pattern}' detected"
            )));
        }
    }

    let mut allowed_imports_used = Vec::new();
    for line in &lines {
        check_imports(line, &mut allowed_imports_used)?;
    }

    Ok(GuardVerdict {
        allowed_imports_used,
        line_count: lines.len(),
        byte_len: source.len(),
    })
}
