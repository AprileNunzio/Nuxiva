const FUNCTION_WORDS: &[&str] = &[
    "il",
    "lo",
    "la",
    "i",
    "gli",
    "le",
    "l",
    "un",
    "uno",
    "una",
    "di",
    "del",
    "dello",
    "della",
    "dei",
    "degli",
    "delle",
    "d",
    "a",
    "al",
    "allo",
    "alla",
    "ai",
    "agli",
    "alle",
    "in",
    "nel",
    "nello",
    "nella",
    "nei",
    "negli",
    "nelle",
    "su",
    "sul",
    "sulla",
    "sui",
    "sulle",
    "con",
    "per",
    "tra",
    "fra",
    "e",
    "ed",
    "o",
    "che",
    "mi",
    "ti",
    "ci",
    "si",
    "me",
    "te",
    "ce",
    "ne",
    "da",
    "dal",
    "dalla",
    "dai",
    "dalle",
    "favore",
    "perfavore",
    "nuxiva",
    "ehi",
    "hey",
    "puoi",
    "potresti",
    "riesci",
    "vorrei",
    "voglio",
    "dammi",
    "fammi",
    "anche",
    "ora",
    "subito",
    "adesso",
    "please",
    "grazie",
    "mio",
    "mia",
    "miei",
    "mie",
    "tuo",
    "tua",
    "suo",
    "sua",
    "nostro",
    "nostra",
    "quello",
    "quella",
    "quelli",
    "quelle",
    "questo",
    "questa",
    "questi",
    "queste",
    "the",
    "of",
    "in",
    "on",
    "at",
    "to",
    "my",
    "our",
    "your",
    "a",
    "an",
    "and",
    "or",
    "can",
    "could",
    "you",
    "would",
    "please",
    "now",
    "el",
    "los",
    "las",
    "del",
    "de",
    "en",
    "y",
    "por",
    "favor",
    "mi",
    "mis",
    "les",
    "des",
    "du",
    "au",
    "aux",
    "dans",
    "et",
    "ou",
    "s",
    "il",
    "vous",
    "plait",
    "der",
    "die",
    "das",
    "den",
    "dem",
    "im",
    "und",
    "bitte",
    "fare",
    "essere",
];

const ACCENTS: &[(char, char)] = &[
    ('à', 'a'),
    ('á', 'a'),
    ('â', 'a'),
    ('ä', 'a'),
    ('ã', 'a'),
    ('å', 'a'),
    ('è', 'e'),
    ('é', 'e'),
    ('ê', 'e'),
    ('ë', 'e'),
    ('ì', 'i'),
    ('í', 'i'),
    ('î', 'i'),
    ('ï', 'i'),
    ('ò', 'o'),
    ('ó', 'o'),
    ('ô', 'o'),
    ('ö', 'o'),
    ('õ', 'o'),
    ('ù', 'u'),
    ('ú', 'u'),
    ('û', 'u'),
    ('ü', 'u'),
    ('ñ', 'n'),
    ('ç', 'c'),
    ('ß', 's'),
    ('ÿ', 'y'),
];

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Token {
    pub word: String,
    pub stem: String,
    pub index: usize,
}

fn fold(c: char) -> char {
    ACCENTS
        .iter()
        .find(|(from, _)| *from == c)
        .map_or(c, |(_, to)| *to)
}

#[must_use]
pub fn normalize(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    for c in text.chars().flat_map(char::to_lowercase) {
        let c = fold(c);
        if c.is_ascii_alphanumeric() {
            out.push(c);
        } else {
            out.push(' ');
        }
    }
    out.split_whitespace().collect::<Vec<_>>().join(" ")
}

#[must_use]
pub fn is_function_word(word: &str) -> bool {
    FUNCTION_WORDS.contains(&word)
}

fn strip_last(word: &mut String, set: &[char]) -> bool {
    if word.chars().count() > 3 && word.ends_with(set) {
        word.pop();
        return true;
    }
    false
}

#[must_use]
pub fn stem(word: &str) -> String {
    let mut w = word.to_owned();
    if w.chars().all(|c| c.is_ascii_digit()) {
        return w;
    }
    strip_last(&mut w, &['s']);
    if strip_last(&mut w, &['a', 'e', 'i', 'o', 'u']) {
        strip_last(&mut w, &['h']);
    }
    if w.ends_with('z') && w.chars().count() > 2 {
        w.pop();
        w.push('c');
    }
    w
}

#[must_use]
pub fn words(text: &str) -> Vec<String> {
    normalize(text)
        .split(' ')
        .filter(|w| !w.is_empty())
        .map(str::to_owned)
        .collect()
}

#[must_use]
pub fn content_tokens(text: &str) -> Vec<Token> {
    words(text)
        .into_iter()
        .enumerate()
        .filter(|(_, w)| !is_function_word(w))
        .map(|(index, word)| Token {
            stem: stem(&word),
            word,
            index,
        })
        .collect()
}

#[must_use]
pub fn phrase(text: &str) -> Vec<String> {
    content_tokens(text).into_iter().map(|t| t.stem).collect()
}
