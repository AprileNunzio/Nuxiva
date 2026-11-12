const STOPWORDS: &[&str] = &[
    "a", "ad", "al", "alla", "alle", "agli", "ai", "che", "chi", "con", "da", "dal", "dalla",
    "dei", "del", "della", "delle", "degli", "di", "e", "ed", "gli", "il", "in", "la", "le", "lo",
    "mi", "ne", "nei", "nel", "nella", "o", "per", "si", "su", "sul", "sulla", "ti", "tra", "fra",
    "un", "una", "uno", "the", "an", "and", "or", "of", "to", "for", "on", "at", "by", "with",
    "from", "is", "are", "be", "it", "its", "me", "my", "you", "your", "les", "des", "du", "au",
    "aux", "et", "ou", "pour", "sur", "avec", "dans", "une", "el", "los", "las", "y", "del", "con",
    "para", "por", "sus", "mis",
];

const FOLD: &[(char, char)] = &[
    ('à', 'a'),
    ('á', 'a'),
    ('â', 'a'),
    ('ã', 'a'),
    ('ä', 'a'),
    ('å', 'a'),
    ('æ', 'a'),
    ('ç', 'c'),
    ('è', 'e'),
    ('é', 'e'),
    ('ê', 'e'),
    ('ë', 'e'),
    ('ì', 'i'),
    ('í', 'i'),
    ('î', 'i'),
    ('ï', 'i'),
    ('ñ', 'n'),
    ('ò', 'o'),
    ('ó', 'o'),
    ('ô', 'o'),
    ('õ', 'o'),
    ('ö', 'o'),
    ('ø', 'o'),
    ('ù', 'u'),
    ('ú', 'u'),
    ('û', 'u'),
    ('ü', 'u'),
    ('ý', 'y'),
    ('ÿ', 'y'),
    ('œ', 'o'),
    ('ß', 's'),
];

#[must_use]
pub fn fold_char(c: char) -> char {
    FOLD.iter()
        .find(|(from, _)| *from == c)
        .map_or(c, |(_, to)| *to)
}

#[must_use]
pub fn normalize(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    let mut space = true;
    for c in text.chars().flat_map(char::to_lowercase).map(fold_char) {
        if c.is_alphanumeric() {
            out.push(c);
            space = false;
        } else if !space {
            out.push(' ');
            space = true;
        }
    }
    if out.ends_with(' ') {
        out.pop();
    }
    out
}

#[must_use]
pub fn is_stopword(word: &str) -> bool {
    STOPWORDS.contains(&word)
}

#[must_use]
pub fn tokens(text: &str) -> Vec<String> {
    normalize(text)
        .split(' ')
        .filter(|w| w.chars().count() >= 3 && !is_stopword(w))
        .map(str::to_owned)
        .collect()
}

#[must_use]
pub fn has_control(text: &str) -> bool {
    text.chars()
        .any(|c| c.is_control() && c != '\n' && c != '\t')
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn folds_accents_and_punctuation() {
        assert_eq!(
            normalize("  Com'è fatta, la MEDUSA?! "),
            "com e fatta la medusa"
        );
    }

    #[test]
    fn drops_stopwords_and_short_words() {
        assert_eq!(tokens("Mi mostri una medusa"), vec!["mostri", "medusa"]);
    }

    #[test]
    fn detects_control_characters() {
        assert!(has_control("a\u{0007}b"));
        assert!(!has_control("riga\nnuova"));
    }
}
