use regex::{Regex, RegexBuilder};

use crate::ranking::RankError;

const SIZE_LIMIT: usize = 256 << 20;
const MAX_SCAN: usize = 20_000;
const MIN_NAME: usize = 3;
const MAX_NAMES: usize = 512;
const MAX_UNITS: usize = 18;
const MIN_UNITS: usize = 12;
const WINDOW: usize = 40;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Level {
    Public,
    Personal,
    Sensitive,
}

impl Level {
    #[must_use]
    pub const fn name(self) -> &'static str {
        match self {
            Self::Public => "public",
            Self::Personal => "personal",
            Self::Sensitive => "sensitive",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Verdict {
    Level(Level),
    Defer,
}

const IBAN: &str = r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){3,7}(?:\s?[A-Z0-9]{1,4})?\b";
const FISCAL: &str = r"\b[A-Z]{6}\d{2}[A-EHLMPR-T]\d{2}[A-Z]\d{3}[A-Z]\b";
const SECRETS: &str =
    r"\b(?:password|passcode|pin|otp|cvv|cvc|codice (?:segreto|di sicurezza|pin))\b";
const MEDICAL: &str = concat!(
    r"\b(?:analisi del sangue|esami del sangue|emocromo|referto|referti|diagnosi|terapia|farmac[oi]|",
    r"prescrizione|ricetta medica|glicemia|colesterolo|trigliceridi|emoglobina|creatinina|",
    r"pressione arteriosa|ricovero|malattia|patologia|sintom[oi]|vaccin[oi]|gravidanza|",
    r"blood test|lab results?|diagnos[ie]s|medication|prescription|cholesterol|pregnan(?:t|cy)|",
    r"análisis de sangre|diagnóstico|receta médica|analyses? de sang|ordonnance)\b",
);
const EMAIL: &str = r"\b[\w.+-]{1,64}@[\w-]{1,63}(?:\.[\w-]{1,63})+\b";
const PHONE: &str = r"(?:^|[^\w+])(?:\+\d{1,3}[\s.-]?\d|[03]\d)(?:[\s.-]?\d){7,10}(?:\D|$)";
const FAMILY: &str = concat!(
    r"\b(?:mia moglie|mio marito|mio figlio|mia figlia|mio padre|mia madre|mio fratello|mia sorella|",
    r"la mia compagna|il mio compagno|abito (?:a|in)|il mio indirizzo|stipendio|conto corrente|",
    r"my wife|my husband|my son|my daughter|my address|my salary|bank account)\b",
);

#[derive(Debug)]
pub struct PrivacyDetector {
    sensitive: Vec<Regex>,
    personal: Vec<Regex>,
}

fn build(pattern: &str, insensitive: bool) -> Result<Regex, RankError> {
    RegexBuilder::new(pattern)
        .case_insensitive(insensitive)
        .size_limit(SIZE_LIMIT)
        .build()
        .map_err(|_| RankError::NotFinite)
}

fn safe_char(c: char) -> bool {
    c.is_ascii()
        || matches!(c, '\u{aa}' | '\u{ba}')
        || (('\u{c0}'..='\u{24f}').contains(&c)
            && !matches!(c, '\u{d7}' | '\u{f7}' | '\u{130}' | '\u{131}' | '\u{17f}'))
}

fn control(c: char) -> bool {
    ('\u{1c}'..='\u{1f}').contains(&c)
}

fn luhn(digits: &[u32]) -> bool {
    let total: u32 = digits
        .iter()
        .rev()
        .enumerate()
        .map(|(index, digit)| {
            let value = if index % 2 == 1 {
                digit.saturating_mul(2)
            } else {
                *digit
            };
            if value > 9 {
                value.saturating_sub(9)
            } else {
                value
            }
        })
        .sum();
    total % 10 == 0
}

fn is_digit(chars: &[char], at: usize) -> bool {
    chars.get(at).is_some_and(char::is_ascii_digit)
}

fn is_sep(chars: &[char], at: usize) -> bool {
    chars.get(at).is_some_and(|c| matches!(c, ' ' | '-'))
}

fn walk(
    chars: &[char],
    start: usize,
    units: usize,
    at: usize,
    dead: &mut [[bool; WINDOW]],
) -> Option<usize> {
    let offset = at.checked_sub(start)?;
    if offset >= WINDOW {
        return None;
    }
    if dead
        .get(units)
        .is_some_and(|row| row.get(offset).copied().unwrap_or(true))
    {
        return None;
    }
    if units < MAX_UNITS && is_digit(chars, at) {
        if is_sep(chars, at.saturating_add(1)) {
            if let Some(end) = walk(
                chars,
                start,
                units.saturating_add(1),
                at.saturating_add(2),
                dead,
            ) {
                return Some(end);
            }
        }
        if let Some(end) = walk(
            chars,
            start,
            units.saturating_add(1),
            at.saturating_add(1),
            dead,
        ) {
            return Some(end);
        }
    }
    if units >= MIN_UNITS && is_digit(chars, at) && !is_digit(chars, at.saturating_add(1)) {
        return Some(at.saturating_add(1));
    }
    if let Some(cell) = dead.get_mut(units).and_then(|row| row.get_mut(offset)) {
        *cell = true;
    }
    None
}

fn card(chars: &[char]) -> bool {
    let mut index = 0;
    while index < chars.len() {
        let starts =
            is_digit(chars, index) && (index == 0 || !is_digit(chars, index.saturating_sub(1)));
        if starts {
            let mut dead = [[false; WINDOW]; MAX_UNITS + 1];
            if let Some(end) = walk(chars, index, 0, index, &mut dead) {
                let digits: Vec<u32> = chars
                    .get(index..end)
                    .unwrap_or_default()
                    .iter()
                    .filter_map(|c| c.to_digit(10))
                    .collect();
                if luhn(&digits) {
                    return true;
                }
                index = end;
                continue;
            }
        }
        index = index.saturating_add(1);
    }
    false
}

impl PrivacyDetector {
    pub fn new() -> Result<Self, RankError> {
        Ok(Self {
            sensitive: vec![
                build(IBAN, false)?,
                build(FISCAL, true)?,
                build(SECRETS, true)?,
                build(MEDICAL, true)?,
            ],
            personal: vec![
                build(EMAIL, false)?,
                build(PHONE, false)?,
                build(FAMILY, true)?,
            ],
        })
    }

    fn named(names: Option<&Regex>, lowered: &str) -> bool {
        names.is_some_and(|regex| regex.is_match(lowered))
    }

    fn classify(&self, text: &str, names: Option<&Regex>) -> Level {
        let body: String = text.chars().take(MAX_SCAN).collect();
        if body.trim().is_empty() {
            return Level::Public;
        }
        let chars: Vec<char> = body.chars().collect();
        if card(&chars) || self.sensitive.iter().any(|regex| regex.is_match(&body)) {
            return Level::Sensitive;
        }
        if self.personal.iter().any(|regex| regex.is_match(&body))
            || Self::named(names, &body.to_lowercase())
        {
            return Level::Personal;
        }
        Level::Public
    }

    pub fn classify_all(&self, texts: &[String], names: &[String]) -> Result<Verdict, RankError> {
        if names.len() > MAX_NAMES {
            return Ok(Verdict::Defer);
        }
        let inputs = texts
            .iter()
            .map(String::as_str)
            .chain(names.iter().map(String::as_str));
        let exotic = inputs
            .flat_map(str::chars)
            .any(|c| !safe_char(c) || control(c));
        if exotic {
            return Ok(Verdict::Defer);
        }
        let usable: Vec<String> = names
            .iter()
            .filter(|name| name.chars().count() >= MIN_NAME)
            .map(|name| regex::escape(name))
            .collect();
        let pattern = (!usable.is_empty()).then(|| format!(r"\b(?:{})\b", usable.join("|")));
        let name_regex = match pattern {
            Some(pattern) => Some(build(&pattern, false)?),
            None => None,
        };
        let level = texts
            .iter()
            .map(|text| self.classify(text, name_regex.as_ref()))
            .max()
            .unwrap_or(Level::Public);
        Ok(Verdict::Level(level))
    }
}
