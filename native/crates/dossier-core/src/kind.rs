use serde::{Deserialize, Serialize};

pub const SCHEMA: &str = "nuxiva.fascicolo/1";
pub const REQUIRED_KEYS: [&str; 6] = [
    "schema",
    "file",
    "operazione",
    "livello",
    "autore",
    "creato",
];

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Level {
    Lampo,
    Standard,
    Progetto,
}

impl Level {
    #[must_use]
    pub fn parse(text: &str) -> Option<Self> {
        match text {
            "lampo" => Some(Self::Lampo),
            "standard" => Some(Self::Standard),
            "progetto" => Some(Self::Progetto),
            _ => None,
        }
    }

    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Lampo => "lampo",
            Self::Standard => "standard",
            Self::Progetto => "progetto",
        }
    }

    #[must_use]
    pub fn required(self) -> &'static [Kind] {
        match self {
            Self::Lampo => &[Kind::Richiesta, Kind::Esito],
            Self::Standard => &[Kind::Richiesta, Kind::Contesto, Kind::Piano, Kind::Esito],
            Self::Progetto => &[
                Kind::Richiesta,
                Kind::Contesto,
                Kind::Piano,
                Kind::Passo,
                Kind::Verifica,
                Kind::Esito,
            ],
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Kind {
    Richiesta,
    Contesto,
    Piano,
    Passo,
    Verifica,
    Esito,
}

impl Kind {
    #[must_use]
    pub fn parse(text: &str) -> Option<Self> {
        match text {
            "richiesta" => Some(Self::Richiesta),
            "contesto" => Some(Self::Contesto),
            "piano" => Some(Self::Piano),
            "passo" => Some(Self::Passo),
            "verifica" => Some(Self::Verifica),
            "esito" => Some(Self::Esito),
            _ => None,
        }
    }

    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Richiesta => "richiesta",
            Self::Contesto => "contesto",
            Self::Piano => "piano",
            Self::Passo => "passo",
            Self::Verifica => "verifica",
            Self::Esito => "esito",
        }
    }

    #[must_use]
    pub const fn sections(self) -> &'static [&'static str] {
        match self {
            Self::Richiesta => &["request", "origin"],
            Self::Contesto => &["agents", "signals"],
            Self::Piano => &["goal", "criteria", "steps", "risks"],
            Self::Passo => &["goal", "tool", "result", "check", "status"],
            Self::Verifica => &["criteria", "evidence", "verdict"],
            Self::Esito => &["summary", "answer", "timing"],
        }
    }

    #[must_use]
    pub const fn fixed_name(self) -> Option<&'static str> {
        match self {
            Self::Richiesta => Some("00-richiesta.md"),
            Self::Contesto => Some("01-contesto.md"),
            Self::Piano => Some("02-piano.md"),
            Self::Passo => None,
            Self::Verifica => Some("90-verifica.md"),
            Self::Esito => Some("99-esito.md"),
        }
    }

    #[must_use]
    pub fn of_name(name: &str) -> Option<Self> {
        if let Some(step) = name.strip_prefix("passi/") {
            return step_name(step).then_some(Self::Passo);
        }
        [
            Self::Richiesta,
            Self::Contesto,
            Self::Piano,
            Self::Verifica,
            Self::Esito,
        ]
        .into_iter()
        .find(|k| k.fixed_name() == Some(name))
    }
}

fn step_name(name: &str) -> bool {
    let Some(stem) = name.strip_suffix(".md") else {
        return false;
    };
    let mut parts = stem.splitn(2, '-');
    let number = parts.next().unwrap_or("");
    let slug = parts.next().unwrap_or("");
    number.len() == 2
        && number.bytes().all(|b| b.is_ascii_digit())
        && number != "00"
        && !slug.is_empty()
        && slug.len() <= 48
        && slug
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-')
        && !slug.starts_with('-')
        && !slug.ends_with('-')
}

#[must_use]
pub fn step_file(number: u8, slug: &str) -> Option<String> {
    let clean: String = slug
        .chars()
        .flat_map(char::to_lowercase)
        .map(|c| if c.is_ascii_alphanumeric() { c } else { '-' })
        .collect();
    let mut compact = String::new();
    for part in clean.split('-').filter(|p| !p.is_empty()) {
        if !compact.is_empty() {
            compact.push('-');
        }
        compact.push_str(part);
    }
    let compact: String = compact.chars().take(48).collect();
    let compact = compact.trim_end_matches('-');
    if !(1..=99).contains(&number) || compact.is_empty() {
        return None;
    }
    Some(format!("passi/{number:02}-{compact}.md"))
}
