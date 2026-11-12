use std::collections::BTreeSet;

use regex::Regex;

pub const MAX_TEXT: usize = 16_000;
const MAX_ALIASES: usize = 32;
const MAX_ALIAS: usize = 64;
const RECENT_PARTNER_S: f64 = 60.0;

const FILLER: &str = r"(?i)^\W*(?:mh+|m+|eh+|ah+|oh+|boh|mah|ok(?:ay)?|va be(?:ne)?|beh|allora|niente|nulla|ahah\w*)\W*$";
const ANSWER: &str = r"(?i)^\W*(?:s[iì]|no|certo|esatto|giusto|perfetto|grazie|ok|va bene|d'accordo|fallo|procedi|annulla|lascia (?:stare|perdere)|non importa)\b";
const REQUEST: &str = r"(?i)\?\s*$|^\W*(?:e\s+)?(?:come|cosa|cos'|dove|quando|quanto|quant[aei]|quale|quali|perch[eé]|dimmi|dammi|fammi|mostra|apri|chiudi|accendi|spegni|metti|togli|alza|abbassa|cerca|trova|calcola|crea|aggiungi|leggi|ricorda|ricordami|imposta|attiva|disattiva|avvia|ferma|riproduci|manda|invia|chiama|prenota|spiega|traduci|continua|ripeti|puoi|potresti|sai|conosci)\b";
const COMMAND: &str = r"(?i)^\W*(?:accendi|spegni|metti|alza|abbassa|apri|chiudi|avvia|ferma|imposta|attiva|disattiva|riproduci|mostrami|dimmi|ricordami|aggiungi|cerca|chiama|manda|leggimi|calcola)\b";
const SECOND_PERSON: &str =
    r"(?i)\b(?:tu|ti|te|tuo|tua|puoi|sai|hai|potresti|vorresti|pensi|dimmi|fammi)\b";
const WORD: &str = r"(?i)[a-zà-ÿ]{4,}";
const FIRST_WORD: &str = r"^\W*([A-Za-zÀ-ÿ']+)";
const WAKE_PREFIX: &str = r"(?i)^(?:hey|hei|ehi|hi|ok|okay)\s+";

#[derive(Debug, Clone, Default, PartialEq)]
pub struct Context {
    pub alone: bool,
    pub facing: bool,
    pub asked_question: bool,
    pub since_reply: f64,
    pub last_turn: Option<String>,
    pub present_names: Vec<String>,
    pub alone_score: f64,
    pub threshold: f64,
    pub same_speaker: Option<bool>,
    pub voices_active: Option<u32>,
    pub mixed_speakers: Option<bool>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Judgement {
    pub directed: bool,
    pub score: f64,
    pub reasons: Vec<&'static str>,
    pub fallback: &'static str,
}

impl Judgement {
    #[must_use]
    pub fn reason(&self) -> String {
        if self.reasons.is_empty() {
            self.fallback.to_owned()
        } else {
            self.reasons.join(", ")
        }
    }

    fn fixed(directed: bool, score: f64, reason: &'static str) -> Self {
        Self {
            directed,
            score,
            reasons: Vec::new(),
            fallback: reason,
        }
    }
}

#[derive(Debug, Clone)]
pub struct AddresseeRules {
    name: Regex,
    third: Regex,
    filler: Regex,
    answer: Regex,
    request: Regex,
    command: Regex,
    second: Regex,
    word: Regex,
    first: Regex,
}

fn alias_list(name: &str, aliases: &[String]) -> Vec<String> {
    let prefix = Regex::new(WAKE_PREFIX).ok();
    let trimmed = name.trim();
    let clean = prefix.map_or_else(
        || trimmed.to_owned(),
        |p| p.replace(trimmed, "").trim().to_owned(),
    );
    let primary = if clean.is_empty() {
        "nuxiva".to_owned()
    } else {
        clean.to_lowercase()
    };
    let mut list: Vec<String> = aliases
        .iter()
        .take(MAX_ALIASES)
        .map(|a| a.trim().to_lowercase())
        .filter(|a| !a.is_empty() && a.len() <= MAX_ALIAS)
        .collect();
    if !list.contains(&primary) {
        list.insert(0, primary.clone());
    }
    if primary == "nuxiva" && !list.iter().any(|a| a == "attena") {
        list.push("attena".to_owned());
    }
    list
}

impl AddresseeRules {
    pub fn new(name: &str, aliases: &[String]) -> Result<Self, regex::Error> {
        let pattern = alias_list(name, aliases)
            .iter()
            .map(|a| regex::escape(a))
            .collect::<Vec<_>>()
            .join("|");
        Ok(Self {
            name: Regex::new(&format!(r"(?i)\b(?:{pattern})\b"))?,
            third: Regex::new(&format!(
                r"(?i)\b(?:lui|lei|(?:{pattern}) (?:è|e'|ha|fa|sta)|il computer|questo coso)\b"
            ))?,
            filler: Regex::new(FILLER)?,
            answer: Regex::new(ANSWER)?,
            request: Regex::new(REQUEST)?,
            command: Regex::new(COMMAND)?,
            second: Regex::new(SECOND_PERSON)?,
            word: Regex::new(WORD)?,
            first: Regex::new(FIRST_WORD)?,
        })
    }

    #[must_use]
    pub fn named(&self, text: &str) -> bool {
        self.name.is_match(text) && !self.third.is_match(text)
    }

    fn words(&self, text: &str) -> BTreeSet<String> {
        let lower = text.to_lowercase();
        self.word
            .find_iter(&lower)
            .map(|m| m.as_str().to_owned())
            .collect()
    }

    #[must_use]
    pub fn overlap(&self, previous: &str, text: &str) -> f64 {
        let before = self.words(previous);
        let now = self.words(text);
        #[allow(clippy::cast_precision_loss)]
        let shared = now.intersection(&before).count() as f64;
        #[allow(clippy::cast_precision_loss)]
        let total = now.len().max(1) as f64;
        shared / total
    }

    fn others_named(&self, text: &str, names: &[String]) -> bool {
        let Some(first) = self.first.captures(text).and_then(|c| c.get(1)) else {
            return false;
        };
        let first = first.as_str().to_lowercase();
        !first.is_empty() && names.iter().any(|n| n.to_lowercase() == first)
    }

    #[must_use]
    pub fn judge(&self, text: &str, ctx: &Context) -> Judgement {
        if text.len() > MAX_TEXT {
            return Judgement::fixed(false, 0.0, "testo troppo lungo");
        }
        if self.named(text) {
            return Judgement::fixed(true, 1.0, "mi ha chiamato per nome");
        }
        let mut score = if ctx.alone { ctx.alone_score } else { 0.0 };
        let mut reasons: Vec<&'static str> = Vec::new();
        if self.filler.is_match(text) {
            return Judgement::fixed(false, 0.0, "intercalare");
        }
        if self.answer.is_match(text) && ctx.asked_question {
            return Judgement::fixed(true, 0.9, "risposta alla mia domanda");
        }
        if self.command.is_match(text) {
            score += 0.45;
            reasons.push("comando");
        } else if self.request.is_match(text) {
            score += 0.35;
            reasons.push("richiesta");
        }
        if self.second.is_match(text) {
            score += 0.15;
            reasons.push("rivolto a me");
        }
        if ctx.facing {
            score += 0.2;
            reasons.push("guarda lo schermo");
        }
        if ctx
            .last_turn
            .as_deref()
            .is_some_and(|last| self.overlap(last, text) >= 0.25)
        {
            score += 0.2;
            reasons.push("stesso argomento");
        }
        if ctx.since_reply < 12.0 {
            score += 0.15;
        }
        if self.others_named(text, &ctx.present_names) {
            score -= 0.6;
            reasons.push("parla con un'altra persona");
        }
        if self.third.is_match(text) {
            score -= 0.3;
            reasons.push("parla di me in terza persona");
        }
        if !ctx.alone && !ctx.facing {
            score -= 0.1;
        }
        if ctx.same_speaker == Some(true) && ctx.since_reply < RECENT_PARTNER_S {
            score += 0.15;
            reasons.push("stessa persona di prima");
        }
        if ctx.voices_active.is_some_and(|n| n >= 2) && !ctx.facing {
            score -= 0.1;
            reasons.push("più voci nella stanza");
        }
        if ctx.mixed_speakers == Some(true) {
            score -= 0.15;
            reasons.push("più persone nella stessa frase");
        }
        Judgement {
            directed: score >= ctx.threshold,
            score,
            reasons,
            fallback: "conversazione generica",
        }
    }
}
