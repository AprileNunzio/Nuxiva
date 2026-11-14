const MAX_TEXT_CHARS: usize = 2_000;
const MIN_TEXT_CHARS: usize = 2;
const FOLLOW_UP_MS: u64 = 12_000;

const COMMAND_STARTS: [&str; 40] = [
    "accendi",
    "spegni",
    "apri",
    "chiudi",
    "metti",
    "togli",
    "cerca",
    "trova",
    "scrivi",
    "leggi",
    "dimmi",
    "dammi",
    "fammi",
    "mostra",
    "avvia",
    "ferma",
    "imposta",
    "ricordami",
    "chiama",
    "invia",
    "manda",
    "prepara",
    "crea",
    "turn",
    "open",
    "close",
    "set",
    "play",
    "stop",
    "show",
    "tell",
    "give",
    "find",
    "search",
    "write",
    "read",
    "remind",
    "call",
    "send",
    "create",
];

const QUESTION_STARTS: [&str; 20] = [
    "come", "cosa", "che", "chi", "dove", "quando", "perche", "quanto", "quale", "puoi", "riesci",
    "how", "what", "who", "where", "when", "why", "can", "could", "is",
];

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GateVerdict {
    Address,
    Ignore(&'static str),
}

#[derive(Debug, Clone)]
pub struct Gatekeeper {
    names: Vec<String>,
    follow_up_ms: u64,
}

fn normalise(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    let mut space = true;
    for c in text.chars() {
        if c.is_alphanumeric() || c == '?' {
            out.extend(c.to_lowercase());
            space = false;
        } else if !space {
            out.push(' ');
            space = true;
        }
    }
    out.trim().to_owned()
}

fn words(text: &str) -> impl Iterator<Item = &str> {
    text.split(' ').filter(|w| !w.is_empty())
}

impl Gatekeeper {
    #[must_use]
    pub fn new<I, S>(names: I) -> Self
    where
        I: IntoIterator<Item = S>,
        S: AsRef<str>,
    {
        let mut names: Vec<String> = names
            .into_iter()
            .map(|n| normalise(n.as_ref()))
            .filter(|n| !n.is_empty())
            .collect();
        names.sort();
        names.dedup();
        Self {
            names,
            follow_up_ms: FOLLOW_UP_MS,
        }
    }

    #[must_use]
    pub fn with_follow_up_ms(mut self, ms: u64) -> Self {
        self.follow_up_ms = ms.clamp(1, 120_000);
        self
    }

    fn named(&self, text: &str) -> bool {
        words(text).any(|w| self.names.iter().any(|n| n == w))
    }

    fn actionable(text: &str) -> bool {
        if text.contains('?') {
            return true;
        }
        let Some(first) = words(text).next() else {
            return false;
        };
        COMMAND_STARTS.contains(&first) || QUESTION_STARTS.contains(&first)
    }

    #[must_use]
    pub fn judge(&self, text: &str, verified: bool, since_last_ms: Option<u64>) -> GateVerdict {
        if text.chars().count() > MAX_TEXT_CHARS {
            return GateVerdict::Ignore("too_long");
        }
        let clean = normalise(text);
        if clean.chars().count() < MIN_TEXT_CHARS {
            return GateVerdict::Ignore("too_short");
        }
        if self.named(&clean) {
            return GateVerdict::Address;
        }
        let in_conversation = since_last_ms.is_some_and(|ms| ms <= self.follow_up_ms);
        if verified && in_conversation && Self::actionable(&clean) {
            return GateVerdict::Address;
        }
        if !verified {
            return GateVerdict::Ignore("not_addressed_unverified");
        }
        GateVerdict::Ignore("not_addressed")
    }
}
