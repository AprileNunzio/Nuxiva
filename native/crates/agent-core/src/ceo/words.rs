use std::collections::{BTreeSet, HashSet};
use std::sync::LazyLock;

use regex::{Regex, RegexBuilder};

use super::lexicon;

pub const STEM: usize = 5;
pub const MAX_QUERY: usize = 4096;

static STOPWORDS: LazyLock<HashSet<&'static str>> =
    LazyLock::new(|| lexicon::STOPWORDS.split_whitespace().collect());
static GENERIC: LazyLock<HashSet<&'static str>> =
    LazyLock::new(|| lexicon::GENERIC.split_whitespace().collect());
static CONVERSATIONAL: LazyLock<Vec<Regex>> = LazyLock::new(|| {
    [lexicon::GREETING, lexicon::SMALLTALK, lexicon::IDENTITY]
        .iter()
        .filter_map(|p| {
            RegexBuilder::new(p)
                .case_insensitive(true)
                .size_limit(1 << 22)
                .build()
                .ok()
        })
        .collect()
});

fn python_space(c: char) -> bool {
    c.is_whitespace() || ('\u{1c}'..='\u{1f}').contains(&c)
}

#[must_use]
pub fn clip(text: &str) -> &str {
    text.char_indices()
        .nth(MAX_QUERY)
        .map_or(text, |(at, _)| text.get(..at).unwrap_or(text))
}

#[must_use]
pub fn normalize(text: &str) -> String {
    let swapped: String = text
        .chars()
        .map(|c| if c == '\u{2019}' || c == '`' { '\'' } else { c })
        .collect();
    swapped.trim_matches(python_space).to_lowercase()
}

fn token_char(c: char) -> bool {
    c.is_ascii_lowercase()
        || c.is_ascii_uppercase()
        || c.is_ascii_digit()
        || matches!(c, '_' | '-' | '\u{131}' | '\u{17f}' | '\u{212a}')
}

#[must_use]
pub fn is_stopword(word: &str) -> bool {
    STOPWORDS.contains(word)
}

#[must_use]
pub fn is_generic(word: &str) -> bool {
    GENERIC.contains(word)
}

#[must_use]
pub fn clean_tokens(text: &str) -> BTreeSet<String> {
    normalize(text)
        .split(|c: char| !token_char(c))
        .filter(|w| w.chars().count() >= 3 && !is_stopword(w))
        .map(str::to_owned)
        .collect()
}

#[must_use]
pub fn stem(token: &str) -> String {
    token.chars().take(STEM).collect()
}

#[must_use]
pub fn stems(text: &str) -> HashSet<String> {
    clean_tokens(text)
        .iter()
        .filter(|t| !is_generic(t))
        .map(|t| stem(t))
        .collect()
}

#[must_use]
pub fn query_stems(text: &str) -> Vec<(String, String)> {
    let mut out: Vec<(String, String)> = Vec::new();
    for token in clean_tokens(text) {
        if is_generic(&token) {
            continue;
        }
        let key = stem(&token);
        match out.iter_mut().find(|(s, _)| *s == key) {
            Some(slot) => slot.1 = token,
            None => out.push((key, token)),
        }
    }
    out
}

#[must_use]
pub fn is_conversational(text: &str) -> bool {
    let clean = normalize(text);
    if clean.is_empty() {
        return true;
    }
    let folded: String = clean
        .chars()
        .map(|c| match c {
            '\u{1c}'..='\u{1f}' => ' ',
            '\u{131}' => 'i',
            '\u{17f}' => 's',
            other => other,
        })
        .collect();
    CONVERSATIONAL.iter().any(|re| re.is_match(&folded))
}

#[must_use]
pub fn word_boundary_contains(haystack: &str, needle: &str) -> bool {
    if needle.is_empty() {
        return false;
    }
    let word = |c: char| c.is_alphanumeric() || c == '_';
    haystack.match_indices(needle).any(|(at, found)| {
        let before = haystack.get(..at).and_then(|h| h.chars().next_back());
        let after = at
            .checked_add(found.len())
            .and_then(|end| haystack.get(end..))
            .and_then(|h| h.chars().next());
        let first = needle.chars().next().is_some_and(word);
        let last = needle.chars().next_back().is_some_and(word);
        let left = before.is_some_and(word) != first;
        let right = after.is_some_and(word) != last;
        left && right
    })
}
