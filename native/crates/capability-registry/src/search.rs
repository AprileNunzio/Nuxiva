use std::collections::{BTreeMap, BTreeSet};

use crate::contract::Contract;

const K1: f64 = 1.2;
const B: f64 = 0.75;

#[must_use]
pub fn tokenize(text: &str) -> Vec<String> {
    text.split(|c: char| !c.is_ascii_alphanumeric())
        .filter(|w| w.len() > 1)
        .map(|w| stem(&w.to_ascii_lowercase()))
        .collect()
}

fn stem(word: &str) -> String {
    for suffix in ["ing", "es", "ed", "s"] {
        if let Some(root) = word.strip_suffix(suffix) {
            if root.len() >= 3 {
                return root.to_owned();
            }
        }
    }
    word.to_owned()
}

fn count(value: usize) -> f64 {
    f64::from(u32::try_from(value).unwrap_or(u32::MAX))
}

#[derive(Debug, Clone, Default)]
pub struct Index {
    docs: Vec<(String, BTreeMap<String, u32>, usize)>,
    frequency: BTreeMap<String, usize>,
    total_len: usize,
}

pub fn document(contract: &Contract) -> Vec<String> {
    let mut words = tokenize(&contract.summary);
    words.extend(tokenize(&contract.id.replace(['_', '.'], " ")));
    for tag in &contract.tags {
        words.extend(tokenize(&tag.replace(['_', '.'], " ")));
        words.extend(tokenize(&tag.replace(['_', '.'], " ")));
    }
    words
}

impl Index {
    pub fn build<'a>(contracts: impl Iterator<Item = &'a Contract>) -> Self {
        let mut index = Self::default();
        for contract in contracts {
            let words = document(contract);
            let mut counts: BTreeMap<String, u32> = BTreeMap::new();
            for word in &words {
                let slot = counts.entry(word.clone()).or_default();
                *slot = slot.saturating_add(1);
            }
            for word in counts.keys() {
                let slot = index.frequency.entry(word.clone()).or_default();
                *slot = slot.saturating_add(1);
            }
            index.total_len = index.total_len.saturating_add(words.len());
            index.docs.push((contract.id.clone(), counts, words.len()));
        }
        index
    }

    pub fn score(&self, query: &str, allowed: &BTreeSet<&str>) -> Vec<(String, f64)> {
        let terms: BTreeSet<String> = tokenize(query).into_iter().collect();
        let n = count(self.docs.len());
        let average = if self.docs.is_empty() {
            1.0
        } else {
            (count(self.total_len) / n).max(1.0)
        };
        let mut hits = Vec::new();
        for (id, counts, len) in &self.docs {
            if !allowed.contains(id.as_str()) {
                continue;
            }
            let mut score = 0.0;
            for term in &terms {
                let tf = f64::from(counts.get(term).copied().unwrap_or(0));
                if tf == 0.0 {
                    continue;
                }
                let df = count(self.frequency.get(term).copied().unwrap_or(0));
                let idf = ((n - df + 0.5) / (df + 0.5) + 1.0).ln();
                let norm = tf * (K1 + 1.0) / (tf + K1 * (1.0 - B + B * count(*len) / average));
                score += idf * norm;
            }
            if score > 0.0 {
                hits.push((id.clone(), score));
            }
        }
        hits.sort_by(|a, b| b.1.total_cmp(&a.1).then_with(|| a.0.cmp(&b.0)));
        hits
    }
}
