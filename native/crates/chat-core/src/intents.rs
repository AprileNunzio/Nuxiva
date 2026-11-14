use regex::{Regex, RegexBuilder};

use crate::patterns::PATTERNS;

pub const CONVERSATION: &str = "conversation";
const SIZE_LIMIT: usize = 1 << 20;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum IntentError {
    Pattern(&'static str),
}

impl std::fmt::Display for IntentError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Pattern(name) => write!(f, "chat.intent.pattern_invalid:{name}"),
        }
    }
}

impl std::error::Error for IntentError {}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Intent {
    pub name: &'static str,
}

#[derive(Debug)]
pub struct IntentTable {
    entries: Vec<(&'static str, Regex)>,
}

impl IntentTable {
    pub fn new() -> Result<Self, IntentError> {
        let mut entries = Vec::with_capacity(PATTERNS.len());
        for (name, pattern) in PATTERNS {
            let compiled = RegexBuilder::new(pattern)
                .case_insensitive(true)
                .size_limit(SIZE_LIMIT)
                .build()
                .map_err(|_| IntentError::Pattern(name))?;
            entries.push((*name, compiled));
        }
        Ok(Self { entries })
    }

    #[must_use]
    pub fn detect(&self, text: &str) -> Intent {
        let name = self
            .entries
            .iter()
            .find(|(_, pattern)| pattern.is_match(text))
            .map_or(CONVERSATION, |(name, _)| *name);
        Intent { name }
    }

    pub fn names(&self) -> impl Iterator<Item = &'static str> + '_ {
        self.entries.iter().map(|(name, _)| *name)
    }
}
