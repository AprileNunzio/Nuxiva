use std::collections::BTreeSet;

use serde::Serialize;

use crate::cues::{
    HOME_NOUNS, HOME_PLACES, PRESENCE_ROOTS, QUESTION_WORDS, SENSOR_ROOTS, STATE_ROOTS,
};
use crate::fuzzy::similarity;
use crate::inventory::Index;
use crate::lexicon::{DOMAIN_WORDS, NEUTRAL, QUANTIFIERS, WHOLE_HOME};
use crate::signals::{self, STEM_FLOOR};
use crate::text::{Token, content_tokens, normalize, words};

pub const RELEVANT: f64 = 0.55;
const NAME_FLOOR: f64 = 0.75;
const NOUN_ANCHOR: f64 = 0.8;
const PLACE_ANCHOR: f64 = 0.6;
const SENSOR_ANCHOR: f64 = 0.65;
const QUESTION_CUE: f64 = 0.8;
const BARE_ANCHOR: f64 = 0.45;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Purpose {
    Command,
    Query,
    Other,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Relevance {
    pub home: bool,
    pub purpose: Purpose,
    pub score: f64,
    pub anchor: f64,
    pub intent: f64,
    pub coverage: f64,
    pub evidence: Vec<&'static str>,
}

#[derive(Default)]
struct Ledger {
    used: BTreeSet<usize>,
    evidence: Vec<&'static str>,
    anchor: f64,
}

impl Ledger {
    fn anchor(&mut self, sure: f64, used: impl IntoIterator<Item = usize>, why: &'static str) {
        if sure <= 0.0 {
            return;
        }
        self.anchor = self.anchor.max(sure);
        self.used.extend(used);
        if !self.evidence.contains(&why) {
            self.evidence.push(why);
        }
    }
}

fn domain_word(word: &str) -> bool {
    DOMAIN_WORDS.iter().any(|(_, generic, specific)| {
        specific.contains(&word) || generic.iter().any(|g| similarity(word, g) >= STEM_FLOOR)
    })
}

fn prefixed(word: &str, roots: &[&str]) -> bool {
    roots.iter().any(|r| word.starts_with(r))
}

fn indices<'a>(tokens: &'a [Token], keep: impl Fn(&Token) -> bool + 'a) -> Vec<usize> {
    tokens.iter().filter(|t| keep(t)).map(|t| t.index).collect()
}

fn ratio(a: usize, b: usize) -> f64 {
    let a = f64::from(u32::try_from(a).unwrap_or(u32::MAX));
    let b = f64::from(u32::try_from(b.max(1)).unwrap_or(u32::MAX));
    a / b
}

fn best_name(index: &Index, tokens: &[Token], skip: &BTreeSet<usize>) -> (f64, BTreeSet<usize>) {
    index
        .entities
        .iter()
        .map(|e| signals::name(index, e, tokens, skip, &[]))
        .filter(|h| h.distinct && h.score >= NAME_FLOOR)
        .fold((0.0, BTreeSet::new()), |acc, h| {
            if h.score > acc.0 {
                (h.score, h.used)
            } else {
                acc
            }
        })
}

fn anchors(index: &Index, text: &str, tokens: &[Token], ledger: &mut Ledger, acted: bool) {
    let verbs = ledger.used.clone();
    let nouns = indices(tokens, |t| HOME_NOUNS.contains(&t.word.as_str()));
    let places = indices(tokens, |t| HOME_PLACES.contains(&t.word.as_str()));
    let skip: BTreeSet<usize> = verbs
        .iter()
        .chain(nouns.iter())
        .chain(places.iter())
        .copied()
        .collect();
    let sturdy: Vec<Token> = tokens
        .iter()
        .filter(|t| t.stem.chars().count() >= 4 || domain_word(&t.word))
        .cloned()
        .collect();
    let domains = signals::domains(index, &sturdy, &skip);
    let domain_sure = if domains.domains.is_empty() {
        0.0
    } else {
        domains.sure.max(STEM_FLOOR)
    };
    ledger.anchor(domain_sure, domains.used.iter().copied(), "domain");
    if let Some(area) = signals::areas(index, tokens, &verbs) {
        let sure = area.sure * if area.partial { 0.75 } else { 1.0 };
        ledger.anchor(sure, area.used.iter().copied(), "area");
    }
    let (name, named) = best_name(index, tokens, &verbs);
    ledger.anchor(name, named, "name");
    let padded = format!(" {} ", normalize(text));
    if WHOLE_HOME
        .iter()
        .any(|p| padded.contains(&format!(" {p} ")))
    {
        let whole = indices(tokens, |t| {
            HOME_NOUNS.contains(&t.word.as_str())
                || HOME_PLACES.contains(&t.word.as_str())
                || QUANTIFIERS.contains(&t.word.as_str())
        });
        ledger.anchor(0.9, whole, "whole_home");
    }
    if !nouns.is_empty() {
        ledger.anchor(NOUN_ANCHOR, nouns, "home_noun");
    }
    if !places.is_empty() {
        ledger.anchor(PLACE_ANCHOR, places, "home_place");
    }
    let sensors = indices(tokens, |t| prefixed(&t.word, SENSOR_ROOTS));
    if !sensors.is_empty() {
        ledger.anchor(SENSOR_ANCHOR, sensors, "measure");
    }
    let quantified = indices(tokens, |t| QUANTIFIERS.contains(&t.word.as_str()));
    if acted && !quantified.is_empty() {
        ledger.anchor(NOUN_ANCHOR, quantified, "everything");
    }
}

fn query(text: &str, all: &[String], tokens: &[Token], ledger: &mut Ledger) -> f64 {
    let raw_question = text.contains('?') || text.contains('\u{bf}');
    let state = indices(tokens, |t| {
        prefixed(&t.word, STATE_ROOTS)
            || prefixed(&t.word, PRESENCE_ROOTS)
            || prefixed(&t.word, SENSOR_ROOTS)
    });
    let questions: Vec<usize> = all
        .iter()
        .enumerate()
        .filter(|(_, w)| QUESTION_WORDS.contains(&w.as_str()))
        .map(|(i, _)| i)
        .collect();
    let mut strength: f64 = 0.0;
    if !state.is_empty() {
        strength = 1.0;
        ledger.used.extend(state);
        ledger.evidence.push("state");
    }
    if !questions.is_empty() || raw_question {
        strength = strength.max(QUESTION_CUE);
        ledger.used.extend(questions);
        ledger.evidence.push("question");
    }
    strength
}

fn coverage(tokens: &[Token], used: &BTreeSet<usize>) -> f64 {
    let content: Vec<&Token> = tokens
        .iter()
        .filter(|t| {
            !NEUTRAL.contains(&t.word.as_str()) && !t.word.chars().all(|c| c.is_ascii_digit())
        })
        .collect();
    if content.is_empty() {
        return 0.0;
    }
    let explained = content.iter().filter(|t| used.contains(&t.index)).count();
    ratio(explained, content.len())
}

fn rounded(value: f64) -> f64 {
    (value * 1000.0).round() / 1000.0
}

#[must_use]
pub fn relevance(index: &Index, text: &str) -> Relevance {
    let all = words(text);
    let tokens = content_tokens(text);
    let mut ledger = Ledger::default();
    let act = signals::action(&all);
    ledger.used.extend(act.iter().map(|a| a.index));
    anchors(index, text, &tokens, &mut ledger, act.is_some());
    let query = query(text, &all, &tokens, &mut ledger);
    let action = act.map_or(0.0, |a| a.sure);
    if action > 0.0 {
        ledger.evidence.push("action");
    }
    let coverage = coverage(&tokens, &ledger.used);
    let intent = action.max(query);
    let anchor = ledger.anchor;
    let score = if anchor <= 0.0 {
        0.0
    } else if intent <= 0.0 {
        anchor * BARE_ANCHOR * coverage
    } else {
        anchor * intent * (0.6 + 0.4 * coverage)
    };
    let score = rounded(score);
    let home = score >= RELEVANT;
    let purpose = if !home {
        Purpose::Other
    } else if action >= query {
        Purpose::Command
    } else {
        Purpose::Query
    };
    Relevance {
        home,
        purpose,
        score,
        anchor,
        intent,
        coverage: rounded(coverage),
        evidence: ledger.evidence,
    }
}
