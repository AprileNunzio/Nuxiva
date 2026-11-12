pub mod lexicon;
pub mod rank;
pub mod words;

use serde::Serialize;

pub use rank::{Card, Index, Learned, Scored, ToolCard, WidgetCard};

pub const MIN_SCORE: f64 = 5.0;
pub const SUPPORT_RATIO: f64 = 0.55;
pub const SUPPORT_SLOTS: usize = 3;
pub const STRONG_SCORE: f64 = 18.0;
pub const STRONG_MARGIN: f64 = 0.3;
pub const LIGHT_RISK: u8 = 2;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Level {
    Lampo,
    Standard,
    Progetto,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Decision {
    pub conversational: bool,
    pub primary: String,
    pub secondaries: Vec<String>,
    pub confidence: f64,
    pub heavy: bool,
    pub level: Level,
    pub needs_reasoning: bool,
    pub ranked: Vec<Scored>,
}

fn round3(value: f64) -> f64 {
    format!("{value:.3}").parse().unwrap_or(value)
}

#[must_use]
pub fn level(primary: Option<&Card>, supports: usize) -> Level {
    let Some(card) = primary else {
        return Level::Lampo;
    };
    if card.project {
        Level::Progetto
    } else if card.heavy || supports > 0 || card.risk > LIGHT_RISK {
        Level::Standard
    } else {
        Level::Lampo
    }
}

#[must_use]
pub fn needs_reasoning(ranked: &[Scored]) -> bool {
    let Some(top) = ranked.first() else {
        return false;
    };
    let second = ranked.get(1).map_or(0.0, |s| s.score);
    let margin = (top.score - second) / top.score.max(1.0);
    !(top.score >= STRONG_SCORE && margin >= STRONG_MARGIN)
}

#[must_use]
pub fn decide(index: &Index, text: &str, learned: &Learned) -> Decision {
    let text = words::clip(text);
    let norm = words::normalize(text);
    if words::is_conversational(&norm) || words::clean_tokens(text).is_empty() {
        return Decision {
            conversational: true,
            primary: String::new(),
            secondaries: Vec::new(),
            confidence: 1.0,
            heavy: false,
            level: Level::Lampo,
            needs_reasoning: false,
            ranked: Vec::new(),
        };
    }
    let ranked = index.rank(text, learned);
    let top = ranked.first().filter(|s| s.score >= MIN_SCORE);
    let Some(top) = top else {
        return Decision {
            conversational: false,
            primary: String::new(),
            secondaries: Vec::new(),
            confidence: 0.5,
            heavy: false,
            level: Level::Lampo,
            needs_reasoning: needs_reasoning(&ranked),
            ranked,
        };
    };
    let runner = ranked.get(1).map_or(0.0, |s| s.score);
    let secondaries: Vec<String> = ranked
        .iter()
        .skip(1)
        .take(SUPPORT_SLOTS)
        .filter(|s| s.score >= top.score * SUPPORT_RATIO && s.score >= MIN_SCORE)
        .map(|s| s.id.clone())
        .collect();
    let margin = (top.score - runner) / top.score.max(1.0);
    let confidence = round3((0.55 + top.score.min(30.0) / 30.0 * 0.25 + margin * 0.2).min(1.0));
    let card = index.card(&top.id);
    Decision {
        conversational: false,
        primary: top.id.clone(),
        heavy: card.is_some_and(|c| c.heavy),
        level: level(card, secondaries.len()),
        secondaries,
        confidence,
        needs_reasoning: needs_reasoning(&ranked),
        ranked,
    }
}

#[cfg(test)]
mod tests;
