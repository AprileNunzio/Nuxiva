use std::cmp::Ordering;
use std::collections::BinaryHeap;
use std::fs;
use std::io::Read;
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

#[derive(PartialEq, Eq)]
struct RankedHit(Hit);

impl Ord for RankedHit {
    fn cmp(&self, other: &Self) -> Ordering {
        other
            .0
            .score
            .cmp(&self.0.score)
            .then_with(|| self.0.path.cmp(&other.0.path))
            .then_with(|| self.0.line.cmp(&other.0.line))
            .then_with(|| self.0.text.cmp(&other.0.text))
    }
}

impl PartialOrd for RankedHit {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
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

fn file_hits(
    root: &Path,
    entry: &FileEntry,
    terms: &[String],
    limit: usize,
    out: &mut BinaryHeap<RankedHit>,
) {
    let Ok(file) = fs::File::open(root.join(&entry.path)) else {
        return;
    };
    let mut bytes = Vec::new();
    let max = Limits::default().max_file_bytes;
    if file
        .take(max.saturating_add(1))
        .read_to_end(&mut bytes)
        .is_err()
        || bytes.len() as u64 > max
        || !is_text(&bytes)
    {
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
        let hit = RankedHit(Hit {
            path: entry.path.clone(),
            line: index.saturating_add(1),
            text: line.trim().chars().take(MAX_LINE_CHARS).collect(),
            score: matched.saturating_mul(10).saturating_add(path_bonus),
        });
        if out.len() < limit {
            out.push(hit);
        } else if let Some(mut worst) = out.peek_mut() {
            if hit < *worst {
                *worst = hit;
            }
        }
    }
}

pub fn search(root: &Path, query: &str, limit: usize) -> Result<Vec<Hit>, ScanError> {
    let terms = terms(query);
    if terms.is_empty() || limit == 0 {
        return Ok(Vec::new());
    }
    let mut hits = BinaryHeap::new();
    for entry in scan(root, Limits::default())? {
        file_hits(root, &entry, &terms, limit, &mut hits);
    }
    Ok(hits
        .into_sorted_vec()
        .into_iter()
        .map(|hit| hit.0)
        .collect())
}
