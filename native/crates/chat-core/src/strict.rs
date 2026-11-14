use regex::{Regex, RegexBuilder};
use unicode_normalization::UnicodeNormalization;

use crate::intents::IntentError;

const SIZE_LIMIT: usize = 1 << 20;
const NUMBER: &str = r"^(?:quanto fa|what is)\s+(-?\d{1,12})\s*(per|times|[×*+−-])\s*(-?\d{1,12})\s*\?\s*(?:rispondi solo con il numero|reply with only the number)\.?$";
const SORT: &str = r"^(?:ordina|sort)\s+(?:in ordine alfabetico|alfabeticamente|alphabetically)\s*:?[ \t]*(.{1,1000})$";
const ITEM: &str = r"^[^\W\d_]+(?:[ '-][^\W\d_]+)*$";
const MAX_ITEMS: usize = 1001;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Outcome {
    Answer(String),
    NoAnswer,
    Defer,
}

#[derive(Debug)]
pub struct StrictReply {
    number: Regex,
    sort: Regex,
    item: Regex,
}

fn build(pattern: &'static str, name: &'static str) -> Result<Regex, IntentError> {
    RegexBuilder::new(pattern)
        .case_insensitive(true)
        .size_limit(SIZE_LIMIT)
        .build()
        .map_err(|_| IntentError::Pattern(name))
}

fn safe_char(c: char) -> bool {
    c.is_ascii() || (('\u{c0}'..='\u{24f}').contains(&c) && c != '\u{d7}' && c != '\u{f7}')
}

fn fold(item: &str) -> String {
    item.to_lowercase().replace('ß', "ss").nfkd().collect()
}

fn operate(left: i128, operation: &str, right: i128) -> Option<i128> {
    match operation.to_lowercase().as_str() {
        "per" | "times" | "×" | "*" => left.checked_mul(right),
        "+" => left.checked_add(right),
        _ => left.checked_sub(right),
    }
}

impl StrictReply {
    pub fn new() -> Result<Self, IntentError> {
        Ok(Self {
            number: build(NUMBER, "strict_number")?,
            sort: build(SORT, "strict_sort")?,
            item: build(ITEM, "strict_item")?,
        })
    }

    #[must_use]
    pub fn deterministic(&self, text: &str) -> Outcome {
        if text.chars().any(|c| ('\u{1c}'..='\u{1f}').contains(&c)) {
            return Outcome::Defer;
        }
        let trimmed = text.trim();
        if let Some(found) = self.number.captures(trimmed) {
            let (Some(left), Some(operation), Some(right)) =
                (found.get(1), found.get(2), found.get(3))
            else {
                return Outcome::NoAnswer;
            };
            let parsed = (
                left.as_str().parse::<i128>(),
                right.as_str().parse::<i128>(),
            );
            return match parsed {
                (Ok(a), Ok(b)) => operate(a, operation.as_str(), b)
                    .map_or(Outcome::Defer, |value| Outcome::Answer(value.to_string())),
                _ => Outcome::Defer,
            };
        }
        let Some(list) = self.sort.captures(trimmed).and_then(|found| found.get(1)) else {
            return Outcome::NoAnswer;
        };
        let body = list
            .as_str()
            .strip_suffix('.')
            .unwrap_or_else(|| list.as_str());
        let items: Vec<&str> = body.split(',').map(str::trim).collect();
        if items.len() < 2 || items.len() > MAX_ITEMS {
            return Outcome::NoAnswer;
        }
        if items.iter().any(|item| !item.chars().all(safe_char)) {
            return Outcome::Defer;
        }
        if !items.iter().all(|item| self.item.is_match(item)) {
            return Outcome::NoAnswer;
        }
        let mut keyed: Vec<(String, &str)> = items.iter().map(|item| (fold(item), *item)).collect();
        keyed.sort_by(|a, b| a.0.cmp(&b.0));
        Outcome::Answer(
            keyed
                .iter()
                .map(|(_, item)| *item)
                .collect::<Vec<_>>()
                .join(", "),
        )
    }
}
