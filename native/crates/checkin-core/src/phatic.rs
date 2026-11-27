use std::collections::BTreeSet;

use serde::Serialize;

use crate::text::{similar, words};

pub const PHATIC: f64 = 0.6;
pub const MAX_LEFTOVER: usize = 1;

const PROTOTYPES: &[&str] = &[
    "come va",
    "come stai",
    "come sta",
    "tutto bene",
    "tutto ok",
    "tutto a posto",
    "tutto regolare",
    "come te la passi",
    "come procede",
    "come andiamo",
    "come butta",
    "come sta andando",
    "che si dice",
    "novita",
    "ci sono novita",
    "aggiornami",
    "how are you",
    "how is it going",
    "how are things",
    "how you doing",
    "whats up",
    "what is up",
    "everything ok",
    "everything fine",
    "all good",
    "any news",
    "whats new",
    "que tal",
    "como estas",
    "como esta",
    "como va",
    "todo bien",
    "que hay de nuevo",
    "como andas",
    "novedades",
    "comment ca va",
    "ca va",
    "comment vas tu",
    "comment allez vous",
    "tout va bien",
    "quoi de neuf",
    "des nouvelles",
];

const COURTESY: &[&str] = &[
    "ciao",
    "salve",
    "buongiorno",
    "buonasera",
    "buonanotte",
    "buon",
    "pomeriggio",
    "ehi",
    "ehila",
    "hey",
    "hi",
    "hello",
    "good",
    "morning",
    "evening",
    "afternoon",
    "hola",
    "buenos",
    "buenas",
    "dias",
    "tardes",
    "noches",
    "bonjour",
    "bonsoir",
    "salut",
    "signore",
    "signora",
    "sir",
    "madam",
    "senor",
    "monsieur",
    "madame",
    "grazie",
    "thanks",
    "gracias",
    "merci",
    "allora",
    "dunque",
    "so",
    "well",
    "bueno",
    "alors",
    "oggi",
    "today",
    "hoy",
    "aujourd",
    "hui",
    "stasera",
    "tonight",
    "esta",
    "noche",
    "ce",
    "soir",
    "amico",
    "mio",
    "friend",
    "my",
    "amigo",
    "mi",
    "ami",
    "mon",
    "e",
    "and",
    "y",
    "et",
    "tu",
    "te",
    "ti",
    "you",
    "vous",
    "per",
    "favore",
    "please",
    "por",
    "s",
    "il",
    "lo",
    "la",
    "i",
    "gli",
    "le",
    "el",
    "los",
    "las",
    "the",
    "di",
    "de",
    "du",
    "des",
    "a",
    "da",
    "con",
    "with",
    "con",
    "avec",
    "qui",
    "here",
    "aqui",
    "ici",
    "coi",
    "col",
    "con",
    "sui",
    "sul",
    "sulla",
    "sulle",
    "nei",
    "nel",
    "nella",
    "about",
    "on",
    "sur",
    "en",
    "avec",
    "como",
    "con",
    "li",
    "si",
    "yes",
    "ok",
    "okay",
    "va",
    "bene",
    "tutto",
];

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Phatic {
    pub phatic: bool,
    pub score: f64,
    pub prototype: Option<&'static str>,
    pub focus: Vec<String>,
}

fn align(prototype: &[String], sentence: &[String]) -> Option<BTreeSet<usize>> {
    let mut used = BTreeSet::new();
    let mut from = 0_usize;
    for word in prototype {
        let hit = sentence
            .iter()
            .enumerate()
            .skip(from)
            .find(|(i, w)| !used.contains(i) && similar(w, word))
            .map(|(i, _)| i)?;
        used.insert(hit);
        from = hit.saturating_add(1);
    }
    Some(used)
}

fn ratio(a: usize, b: usize) -> f64 {
    let a = f64::from(u32::try_from(a).unwrap_or(u32::MAX));
    let b = f64::from(u32::try_from(b.max(1)).unwrap_or(u32::MAX));
    a / b
}

#[must_use]
pub fn detect(text: &str, names: &[String]) -> Phatic {
    let sentence = words(text);
    let names: BTreeSet<String> = names.iter().flat_map(|n| words(n)).collect();
    let mut best: Option<(&'static str, BTreeSet<usize>)> = None;
    for proto in PROTOTYPES {
        let shape = words(proto);
        if let Some(used) = align(&shape, &sentence) {
            let wins = best.as_ref().is_none_or(|(_, b)| used.len() > b.len());
            if wins {
                best = Some((proto, used));
            }
        }
    }
    let Some((prototype, used)) = best else {
        return Phatic {
            phatic: false,
            score: 0.0,
            prototype: None,
            focus: Vec::new(),
        };
    };
    let leftover: Vec<String> = sentence
        .iter()
        .enumerate()
        .filter(|(i, w)| {
            !used.contains(i) && !COURTESY.contains(&w.as_str()) && !names.contains(w.as_str())
        })
        .map(|(_, w)| w.clone())
        .collect();
    let explained = sentence.len().saturating_sub(leftover.len());
    let score = (ratio(explained, sentence.len()) * 1000.0).round() / 1000.0;
    let phatic = leftover.len() <= MAX_LEFTOVER && score >= PHATIC;
    Phatic {
        phatic,
        score,
        prototype: Some(prototype),
        focus: if phatic { leftover } else { Vec::new() },
    }
}
