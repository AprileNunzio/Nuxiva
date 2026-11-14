use std::collections::VecDeque;

use serde::{Deserialize, Serialize};

use crate::error::{DuplexError, DuplexResult};

const TERMINATORS: [char; 4] = ['.', '!', '?', '…'];
const CLAUSE: [char; 3] = [',', ';', ':'];
const ABBREVIATIONS: [&str; 22] = [
    "sig", "sigg", "sra", "dott", "dr", "prof", "ing", "avv", "ecc", "es", "vs", "etc", "cap",
    "pag", "art", "tel", "mr", "mrs", "ms", "dott.ssa", "eng", "st",
];

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ChunkSettings {
    pub min_chars: usize,
    pub min_clause_chars: usize,
    pub max_wait_ms: u64,
    pub max_chunk_chars: usize,
    pub queue_cap: usize,
}

impl Default for ChunkSettings {
    fn default() -> Self {
        Self {
            min_chars: 12,
            min_clause_chars: 24,
            max_wait_ms: 350,
            max_chunk_chars: 240,
            queue_cap: 8,
        }
    }
}

impl ChunkSettings {
    pub fn from_json(text: &str) -> DuplexResult<Self> {
        if text.len() > 4_096 {
            return Err(DuplexError::TooLarge);
        }
        let s: Self = serde_json::from_str(text).map_err(|_| DuplexError::Parse)?;
        s.validate()?;
        Ok(s)
    }

    pub fn validate(&self) -> DuplexResult<()> {
        let ok = (1..=200).contains(&self.min_chars)
            && (self.min_chars..=400).contains(&self.min_clause_chars)
            && (50..=10_000).contains(&self.max_wait_ms)
            && (self.min_clause_chars.max(32)..=2_000).contains(&self.max_chunk_chars)
            && (1..=64).contains(&self.queue_cap);
        if ok {
            Ok(())
        } else {
            Err(DuplexError::Settings)
        }
    }
}

#[derive(Debug)]
pub struct Chunker {
    settings: ChunkSettings,
    buffer: String,
    last_emit_ms: Option<u64>,
}

fn token_before(text: &str, end: usize) -> &str {
    let head = text.get(..end).unwrap_or("");
    head.rsplit(char::is_whitespace).next().unwrap_or("")
}

fn starts_lower_or_digit(rest: &str) -> bool {
    rest.trim_start()
        .chars()
        .next()
        .is_some_and(|c| c.is_lowercase() || c.is_ascii_digit())
}

fn is_protected_dot(text: &str, at: usize, rest: &str) -> bool {
    let token = token_before(text, at);
    let bare = token.trim_start_matches(['(', '"', '«']);
    let lower = bare.to_lowercase();
    if ABBREVIATIONS.contains(&lower.as_str()) {
        return true;
    }
    let mut chars = bare.chars();
    if bare.contains('.') && bare.chars().all(|c| c.is_alphabetic() || c == '.') {
        return true;
    }
    if let (Some(first), None) = (chars.next(), chars.next()) {
        return first.is_uppercase();
    }
    !bare.is_empty() && bare.chars().all(|c| c.is_ascii_digit()) && starts_lower_or_digit(rest)
}

impl Chunker {
    pub fn new(settings: ChunkSettings) -> DuplexResult<Self> {
        settings.validate()?;
        Ok(Self {
            settings,
            buffer: String::new(),
            last_emit_ms: None,
        })
    }

    fn boundary(&self, last: bool) -> Option<usize> {
        let text = self.buffer.as_str();
        let mut iter = text.char_indices().peekable();
        let mut seen = 0usize;
        while let Some((i, c)) = iter.next() {
            seen = seen.saturating_add(1);
            let end = i.saturating_add(c.len_utf8());
            let is_end = TERMINATORS.contains(&c);
            let is_clause = CLAUSE.contains(&c);
            if !is_end && !is_clause {
                continue;
            }
            let Some((_, next)) = iter.peek().copied() else {
                if is_end && last {
                    return Some(end);
                }
                continue;
            };
            if !next.is_whitespace() {
                continue;
            }
            let rest = text.get(end..).unwrap_or("");
            if is_end {
                if c == '.' && is_protected_dot(text, i, rest) {
                    continue;
                }
                return Some(end);
            }
            if seen >= self.settings.min_clause_chars {
                return Some(end);
            }
        }
        None
    }

    fn soft_split(&self, limit_chars: usize) -> Option<usize> {
        let text = self.buffer.as_str();
        let mut best = None;
        let mut count = 0usize;
        let mut token_start = 0usize;
        for (i, c) in text.char_indices() {
            count = count.saturating_add(1);
            if c.is_whitespace() {
                let token = text.get(token_start..i).unwrap_or("");
                let prev_token_digit = token.chars().last().is_some_and(|d| d.is_ascii_digit());
                if count >= self.settings.min_chars && count <= limit_chars && !token.is_empty() {
                    let after = text.get(i..).unwrap_or("").trim_start();
                    let next_digit = after.chars().next().is_some_and(|d| d.is_ascii_digit());
                    if (!prev_token_digit || !next_digit) && !after.is_empty() {
                        best = Some(i);
                    }
                }
                token_start = i.saturating_add(c.len_utf8());
            }
        }
        best
    }

    fn take(&mut self, end: usize, now_ms: u64, out: &mut Vec<String>) {
        let rest = self.buffer.split_off(end);
        let chunk = std::mem::replace(&mut self.buffer, rest.trim_start().to_owned());
        let chunk = chunk.trim();
        if !chunk.is_empty() {
            out.push(chunk.to_owned());
        }
        self.last_emit_ms = Some(now_ms);
    }

    fn hard_cap(&mut self, now_ms: u64, out: &mut Vec<String>) {
        while self.buffer.chars().count() > self.settings.max_chunk_chars {
            let cap = self.settings.max_chunk_chars;
            let end = self.soft_split(cap).unwrap_or_else(|| {
                self.buffer
                    .char_indices()
                    .nth(cap)
                    .map_or(self.buffer.len(), |(i, _)| i)
            });
            self.take(end, now_ms, out);
        }
    }

    pub fn push(&mut self, token: &str, now_ms: u64) -> Vec<String> {
        if self.last_emit_ms.is_none() {
            self.last_emit_ms = Some(now_ms);
        }
        self.buffer.push_str(token);
        let mut out = Vec::new();
        while let Some(end) = self.boundary(false) {
            self.take(end, now_ms, &mut out);
        }
        self.hard_cap(now_ms, &mut out);
        out
    }

    pub fn poll(&mut self, now_ms: u64) -> Vec<String> {
        let mut out = Vec::new();
        let waited = now_ms.saturating_sub(self.last_emit_ms.unwrap_or(now_ms));
        if waited >= self.settings.max_wait_ms
            && self.buffer.chars().count() >= self.settings.min_chars
            && let Some(end) = self.soft_split(usize::MAX)
        {
            self.take(end, now_ms, &mut out);
        }
        out
    }

    pub fn flush(&mut self, now_ms: u64) -> Vec<String> {
        let mut out = Vec::new();
        while let Some(end) = self.boundary(true) {
            self.take(end, now_ms, &mut out);
        }
        self.hard_cap(now_ms, &mut out);
        let tail = self.buffer.trim().to_owned();
        self.buffer.clear();
        if !tail.is_empty() {
            out.push(tail);
        }
        self.last_emit_ms = None;
        out
    }

    #[must_use]
    pub fn pending_chars(&self) -> usize {
        self.buffer.chars().count()
    }

    pub fn reset(&mut self) {
        self.buffer.clear();
        self.last_emit_ms = None;
    }

    #[must_use]
    pub const fn queue_cap(&self) -> usize {
        self.settings.queue_cap
    }
}

#[derive(Debug, Default)]
pub struct Backlog {
    items: VecDeque<(u32, String)>,
}

impl Backlog {
    pub fn push(&mut self, seq: u32, text: String, cap: usize) -> DuplexResult<()> {
        if self.items.len() >= cap {
            return Err(DuplexError::Capacity);
        }
        self.items.push_back((seq, text));
        Ok(())
    }

    pub fn pop(&mut self) -> Option<(u32, String)> {
        self.items.pop_front()
    }

    pub fn clear(&mut self) -> usize {
        let n = self.items.len();
        self.items.clear();
        n
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.items.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.items.is_empty()
    }
}
