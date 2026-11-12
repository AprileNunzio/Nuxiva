use crate::distress_phrases::{
    HYPOTHETICAL, HYPOTHETICAL_PAIRS, NEGATORS, NO, PHRASES, REPORTED, YES,
};
use crate::words::fold;

pub const MAX_TEXT: usize = 4096;
pub const MAX_WORDS: usize = 256;
pub const NEGATION_REACH: usize = 3;
pub const HYPOTHETICAL_FACTOR: f64 = 0.35;
pub const REPORTED_FACTOR: f64 = 0.6;
pub const TASK_FACTOR: f64 = 0.25;
pub const MEDIA_FACTOR: f64 = 0.5;
pub const SHORT_ANSWER: usize = 4;
pub const NEEDS: &[&str] = &[
    "bisogno", "serve", "servono", "need", "needs", "besoin", "necesito", "necesita",
];
pub const TASK_WORDS: &[&str] = &[
    "a", "ad", "con", "with", "to", "on", "avec", "for", "per", "pour", "para",
];

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Cue {
    Help,
    Emergency,
    Medical,
    Threat,
    Fire,
    NotOk,
    Ok,
}

impl Cue {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Help => "help",
            Self::Emergency => "emergency",
            Self::Medical => "medical",
            Self::Threat => "threat",
            Self::Fire => "fire",
            Self::NotOk => "not_ok",
            Self::Ok => "ok",
        }
    }

    const fn alarming(self) -> bool {
        matches!(
            self,
            Self::Help | Self::Emergency | Self::Medical | Self::Threat | Self::Fire
        )
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Answer {
    Ok,
    NotOk,
}

impl Answer {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Ok => "ok",
            Self::NotOk => "not_ok",
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct Detection {
    pub cue: Cue,
    pub phrase: &'static str,
    pub lang: &'static str,
    pub start: usize,
    pub probability: f64,
    pub negated: bool,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Distress {
    pub detections: Vec<Detection>,
    pub help: f64,
    pub threat: f64,
    pub fire: f64,
    pub confidence: f64,
    pub answer: Option<Answer>,
    pub lang: Option<&'static str>,
}

fn words_of(text: &str) -> Vec<String> {
    let spaced: String = text
        .chars()
        .take(MAX_TEXT)
        .map(|c| if c.is_whitespace() { ' ' } else { c })
        .collect();
    fold(&spaced)
        .split(' ')
        .filter(|w| !w.is_empty())
        .take(MAX_WORDS)
        .map(str::to_owned)
        .collect()
}

fn has_run(words: &[String], phrase: &str) -> Option<usize> {
    let parts: Vec<&str> = phrase.split(' ').collect();
    if parts.is_empty() || parts.len() > words.len() {
        return None;
    }
    (0..=words.len().saturating_sub(parts.len())).find(|&i| {
        words
            .get(i..i.saturating_add(parts.len()))
            .is_some_and(|run| run.iter().zip(&parts).all(|(w, p)| w == p))
    })
}

fn ordered() -> Vec<&'static (&'static str, Cue, &'static str, f64)> {
    let mut list: Vec<_> = PHRASES.iter().collect();
    list.sort_by(|a, b| {
        b.0.split(' ')
            .count()
            .cmp(&a.0.split(' ').count())
            .then(a.1.cmp(&b.1))
            .then(a.0.cmp(b.0))
    });
    list
}

fn negator_before(words: &[String], start: usize) -> bool {
    let from = start.saturating_sub(NEGATION_REACH);
    words
        .get(from..start)
        .is_some_and(|before| before.iter().any(|w| NEGATORS.contains(&w.as_str())))
}

fn negated(words: &[String], start: usize) -> bool {
    if negator_before(words, start) {
        return true;
    }
    let from = start.saturating_sub(NEGATION_REACH);
    (from..start).any(|i| {
        words.get(i).is_some_and(|w| NEEDS.contains(&w.as_str())) && negator_before(words, i)
    })
}

fn task_follows(words: &[String], end: usize) -> bool {
    words
        .get(end)
        .is_some_and(|w| TASK_WORDS.contains(&w.as_str()))
}

fn context_factor(words: &[String]) -> f64 {
    let hypothetical = words.iter().any(|w| HYPOTHETICAL.contains(&w.as_str()))
        || HYPOTHETICAL_PAIRS
            .iter()
            .any(|p| has_run(words, p).is_some());
    let reported = REPORTED.iter().any(|p| has_run(words, p).is_some());
    let mut factor = 1.0;
    if hypothetical {
        factor *= HYPOTHETICAL_FACTOR;
    }
    if reported {
        factor *= REPORTED_FACTOR;
    }
    factor
}

fn scan(words: &[String], factor: f64) -> Vec<Detection> {
    let mut used = vec![false; words.len()];
    let mut found = Vec::new();
    for &(phrase, cue, lang, weight) in ordered() {
        let parts = phrase.split(' ').count();
        let mut i = 0_usize;
        while i.saturating_add(parts) <= words.len() {
            let end = i.saturating_add(parts);
            let free = used.get(i..end).is_some_and(|u| u.iter().all(|x| !x));
            let same = words
                .get(i..end)
                .is_some_and(|run| run.iter().zip(phrase.split(' ')).all(|(w, p)| w == p));
            if free && same {
                used.iter_mut().skip(i).take(parts).for_each(|u| *u = true);
                let neg = cue.alarming() && negated(words, i);
                let task = cue == Cue::Help && task_follows(words, end);
                let mut p = weight * factor;
                if task {
                    p *= TASK_FACTOR;
                }
                found.push(Detection {
                    cue,
                    phrase,
                    lang,
                    start: i,
                    probability: p,
                    negated: neg,
                });
                i = end;
            } else {
                i = i.saturating_add(1);
            }
        }
    }
    found.sort_by(|a, b| a.start.cmp(&b.start).then(a.cue.cmp(&b.cue)));
    found
}

fn combine(found: &[Detection], cues: &[Cue]) -> f64 {
    let rest = found
        .iter()
        .filter(|d| !d.negated && cues.contains(&d.cue))
        .fold(1.0, |acc, d| acc * (1.0 - d.probability.clamp(0.0, 1.0)));
    (1.0 - rest).clamp(0.0, 1.0)
}

fn short_answer(words: &[String]) -> Option<Answer> {
    if words.is_empty() || words.len() > SHORT_ANSWER {
        return None;
    }
    let joined = words.join(" ");
    if NO.contains(&joined.as_str()) {
        return Some(Answer::NotOk);
    }
    if YES.contains(&joined.as_str()) || words.first().is_some_and(|w| YES.contains(&w.as_str())) {
        return Some(Answer::Ok);
    }
    None
}

#[must_use]
pub fn analyze(text: &str, asked: bool, media: bool, speech_confidence: f64) -> Distress {
    let words = words_of(text);
    let factor = context_factor(&words);
    let found = scan(&words, factor);
    let help = combine(&found, &[Cue::Help, Cue::Emergency, Cue::Medical]);
    let threat = combine(&found, &[Cue::Threat]);
    let fire = combine(&found, &[Cue::Fire]);
    let alarmed = found
        .iter()
        .any(|d| !d.negated && matches!(d.cue, Cue::Help | Cue::Emergency | Cue::Medical));
    let answer = if alarmed || found.iter().any(|d| d.cue == Cue::NotOk) {
        Some(Answer::NotOk)
    } else if found.iter().any(|d| d.cue == Cue::Ok) {
        Some(Answer::Ok)
    } else if asked {
        short_answer(&words)
    } else {
        None
    };
    let base = if speech_confidence.is_finite() {
        speech_confidence.clamp(0.0, 1.0)
    } else {
        0.0
    };
    let confidence = if media { base * MEDIA_FACTOR } else { base };
    let lang = found.iter().find(|d| !d.negated).map(|d| d.lang);
    Distress {
        detections: found,
        help,
        threat,
        fire,
        confidence,
        answer,
        lang,
    }
}
