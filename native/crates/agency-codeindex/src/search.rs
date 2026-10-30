use std::fs;
use std::path::Path;

use serde::Serialize;

use crate::scan::{FileEntry, Limits, ScanError, scan};

const MAX_LINE_CHARS: usize = 240;
const MAX_TERMS: usize = 8;

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Hit {
    pub path: String,
    pub line: usize,
    pub text: String,
    pub score: usize,
}

fn terms(query: &str) -> Vec<String> {
    let mut out: Vec<String> = query
        .split(|c: char| !(c.is_alphanumeric() || c == '_'))
        .filter(|t| t.chars().count() >= 2)
        .map(str::to_lowercase)
        .collect();
    out.sort();
    out.dedup();
    out.truncate(MAX_TERMS);
    out
}

fn is_text(bytes: &[u8]) -> bool {
    !bytes.iter().take(4096).any(|b| *b == 0)
}

fn file_hits(root: &Path, entry: &FileEntry, terms: &[String], out: &mut Vec<Hit>) {
    let Ok(bytes) = fs::read(root.join(&entry.path)) else {
        return;
    };
    if !is_text(&bytes) {
        return;
    }
    let text = String::from_utf8_lossy(&bytes);
    let path_lower = entry.path.to_lowercase();
    let path_bonus = terms
        .iter()
        .filter(|t| path_lower.contains(t.as_str()))
        .count();
    for (index, line) in text.lines().enumerate() {
        let lower = line.to_lowercase();
        let matched = terms.iter().filter(|t| lower.contains(t.as_str())).count();
        if matched == 0 {
            continue;
        }
        out.push(Hit {
            path: entry.path.clone(),
            line: index.saturating_add(1),
            text: line.trim().chars().take(MAX_LINE_CHARS).collect(),
            score: matched.saturating_mul(10).saturating_add(path_bonus),
        });
    }
}

pub fn search(root: &Path, query: &str, limit: usize) -> Result<Vec<Hit>, ScanError> {
    let terms = terms(query);
    if terms.is_empty() || limit == 0 {
        return Ok(Vec::new());
    }
    let mut hits = Vec::new();
    for entry in scan(root, Limits::default())? {
        file_hits(root, &entry, &terms, &mut hits);
    }
    hits.sort_by(|a, b| {
        b.score
            .cmp(&a.score)
            .then_with(|| a.path.cmp(&b.path))
            .then(a.line.cmp(&b.line))
    });
    hits.truncate(limit);
    Ok(hits)
}
