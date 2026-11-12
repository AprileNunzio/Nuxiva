use std::collections::{HashMap, HashSet};

use regex::{Regex, RegexBuilder};
use serde::{Deserialize, Serialize};

use super::words::{self, is_generic, stem, stems};

pub const PHRASE_BONUS: f64 = 14.0;
pub const LEARNED_STEP: f64 = 2.0;
pub const LEARNED_CAP: u32 = 4;
pub const NAME_BONUS: f64 = 10.0;
pub const MAX_AGENTS: usize = 4096;
pub const MAX_PHRASE: usize = 512;
const FIELDS: [(&str, f64); 7] = [
    ("identity", 3.0),
    ("noun", 4.0),
    ("capability", 1.3),
    ("tool", 1.6),
    ("tool_text", 0.6),
    ("description", 0.9),
    ("keyword", 0.3),
];

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default)]
pub struct ToolCard {
    pub name: String,
    pub description: String,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default)]
pub struct WidgetCard {
    pub name: String,
    pub intents: Vec<String>,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default)]
pub struct Card {
    pub id: String,
    pub name: String,
    pub description: String,
    pub keywords: Vec<String>,
    pub capabilities: Vec<String>,
    pub tools: Vec<ToolCard>,
    pub widgets: Vec<WidgetCard>,
    pub nouns: Vec<String>,
    pub phrases: Vec<String>,
    pub heavy: bool,
    pub project: bool,
    pub risk: u8,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Scored {
    pub id: String,
    pub score: f64,
    pub why: Vec<String>,
}

pub type Learned = HashMap<String, HashMap<String, u32>>;

#[derive(Debug)]
struct Entry {
    card: Card,
    fields: [HashSet<String>; 7],
    keywords: HashSet<String>,
    phrases: Vec<Regex>,
    id_lower: String,
    name_lower: String,
}

#[derive(Debug)]
pub struct Index {
    entries: Vec<Entry>,
    frequency: HashMap<String, usize>,
    total: f64,
}

fn phrase(pattern: &str) -> Option<Regex> {
    if pattern.chars().count() > MAX_PHRASE {
        return None;
    }
    RegexBuilder::new(pattern)
        .case_insensitive(true)
        .size_limit(1 << 20)
        .dfa_size_limit(1 << 20)
        .build()
        .ok()
}

fn entry(card: Card) -> Entry {
    let mut fields: [HashSet<String>; 7] = Default::default();
    let [
        identity,
        noun,
        capability,
        tool,
        tool_text,
        description,
        keyword,
    ] = &mut fields;
    identity.extend(stems(&card.id));
    identity.extend(stems(&card.name));
    for n in &card.nouns {
        noun.extend(stems(n));
    }
    for c in &card.capabilities {
        capability.extend(stems(c));
    }
    for t in &card.tools {
        tool.extend(
            t.name
                .to_lowercase()
                .split('_')
                .filter(|p| p.chars().count() >= 3)
                .map(stem),
        );
        tool_text.extend(stems(&t.description));
    }
    for w in &card.widgets {
        identity.extend(stems(&w.name));
        for i in &w.intents {
            noun.extend(stems(i));
        }
    }
    description.extend(stems(&card.description));
    keyword.extend(
        card.keywords
            .iter()
            .filter(|k| !is_generic(k))
            .map(|k| stem(k)),
    );
    Entry {
        keywords: card.keywords.iter().cloned().collect(),
        phrases: card.phrases.iter().filter_map(|p| phrase(p)).collect(),
        id_lower: card.id.to_lowercase(),
        name_lower: card.name.to_lowercase(),
        fields,
        card,
    }
}

fn round3(value: f64) -> f64 {
    format!("{value:.3}").parse().unwrap_or(value)
}

impl Index {
    #[must_use]
    pub fn new(cards: Vec<Card>) -> Self {
        let entries: Vec<Entry> = cards.into_iter().take(MAX_AGENTS).map(entry).collect();
        let mut frequency: HashMap<String, usize> = HashMap::new();
        for e in &entries {
            let union: HashSet<&String> = e.fields.iter().flatten().collect();
            for token in union {
                let slot = frequency.entry(token.clone()).or_insert(0);
                *slot = slot.saturating_add(1);
            }
        }
        let count = u32::try_from(entries.len().max(1)).unwrap_or(u32::MAX);
        Self {
            entries,
            frequency,
            total: f64::from(count),
        }
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.entries.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    #[must_use]
    pub fn card(&self, id: &str) -> Option<&Card> {
        self.entries.iter().map(|e| &e.card).find(|c| c.id == id)
    }

    #[must_use]
    pub fn invalid_phrases(&self) -> Vec<(String, String)> {
        self.entries
            .iter()
            .flat_map(|e| {
                e.card
                    .phrases
                    .iter()
                    .filter(|p| phrase(p).is_none())
                    .map(|p| (e.card.id.clone(), p.clone()))
            })
            .collect()
    }

    fn rarity(&self, token: &str) -> f64 {
        let freq = self.frequency.get(token).copied().unwrap_or(1).max(1);
        let freq = f64::from(u32::try_from(freq).unwrap_or(u32::MAX));
        (1.0 + self.total / freq).ln()
    }

    #[must_use]
    pub fn rank(&self, text: &str, learned: &Learned) -> Vec<Scored> {
        let text = words::clip(text);
        let norm = words::normalize(text);
        let wanted = words::query_stems(text);
        let mut out: Vec<Scored> = self
            .entries
            .iter()
            .map(|e| self.score(e, &norm, &wanted, learned))
            .collect();
        out.sort_by(|a, b| b.score.total_cmp(&a.score));
        out
    }

    fn score(
        &self,
        e: &Entry,
        norm: &str,
        wanted: &[(String, String)],
        learned: &Learned,
    ) -> Scored {
        let mut score = 0.0_f64;
        let mut why = Vec::new();
        for (token, original) in wanted {
            let mut best = 0.0_f64;
            let mut kind = "";
            for ((name, weight), set) in FIELDS.iter().zip(e.fields.iter()) {
                if set.contains(token) {
                    let value = weight * self.rarity(token);
                    if value > best {
                        best = value;
                        kind = name;
                    }
                }
            }
            if best > 0.0 {
                if e.keywords.contains(original) || *original == e.id_lower {
                    best *= 1.2;
                }
                score += best;
                why.push(format!("{original}:{kind}"));
            }
            let times = learned
                .get(token)
                .and_then(|row| row.get(&e.card.id))
                .copied()
                .unwrap_or(0);
            if times > 0 {
                score += LEARNED_STEP * f64::from(times.min(LEARNED_CAP));
                why.push(format!("{original}:appreso"));
            }
        }
        let hits = e
            .phrases
            .iter()
            .filter(|re| re.is_match(norm))
            .take(2)
            .count();
        if hits > 0 {
            score += PHRASE_BONUS * f64::from(u32::try_from(hits).unwrap_or(2));
            why.push("frase".to_owned());
        }
        let named = words::word_boundary_contains(norm, &e.id_lower)
            || (e.card.name.chars().count() > 3 && norm.contains(&e.name_lower));
        if named {
            score += NAME_BONUS;
            why.push("nome".to_owned());
        }
        Scored {
            id: e.card.id.clone(),
            score: round3(score),
            why,
        }
    }
}
