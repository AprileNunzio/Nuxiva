use std::collections::HashSet;
use std::hash::BuildHasher;

pub const MAX_TERMS: usize = 4096;
pub const MAX_TERM_CHARS: usize = 60;
pub const MAX_TOKENS: usize = 512;
pub const MAX_SPAN: usize = 3;
const MIN_KEY: usize = 3;
const CONTEXT_BONUS: f64 = 0.03;
const KEY_SHARE: f64 = 0.6;

#[derive(Debug, Clone, PartialEq)]
pub struct Token {
    pub text: String,
    pub prob: f64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Correction {
    pub heard: String,
    pub term: String,
    pub score: f64,
}

#[derive(Debug, Clone)]
struct Term {
    text: String,
    folded: String,
    key: String,
    words: usize,
}

#[derive(Debug, Clone, Default)]
pub struct Lexicon {
    terms: Vec<Term>,
    known: HashSet<String>,
}

fn fold_char(c: char) -> Option<char> {
    let lower = c.to_lowercase().next().unwrap_or(c);
    let base = match lower {
        'à' | 'á' | 'â' | 'ä' | 'ã' | 'å' => 'a',
        'è' | 'é' | 'ê' | 'ë' => 'e',
        'ì' | 'í' | 'î' | 'ï' => 'i',
        'ò' | 'ó' | 'ô' | 'ö' | 'õ' => 'o',
        'ù' | 'ú' | 'û' | 'ü' => 'u',
        'ç' => 'c',
        'ñ' => 'n',
        other => other,
    };
    (base.is_ascii_alphanumeric() || base == ' ').then_some(base)
}

#[must_use]
pub fn fold(text: &str) -> String {
    let raw: String = text
        .chars()
        .map(|c| if c == '\'' || c == '-' { ' ' } else { c })
        .filter_map(fold_char)
        .collect();
    raw.split_whitespace().collect::<Vec<_>>().join(" ")
}

#[must_use]
pub fn phonetic(text: &str) -> String {
    let chars: Vec<char> = fold(text)
        .chars()
        .filter(char::is_ascii_alphanumeric)
        .flat_map(|c| if c == 'x' { vec!['k', 's'] } else { vec![c] })
        .collect();
    let at = |i: usize| chars.get(i).copied().unwrap_or('\0');
    let soft = |c: char| c == 'e' || c == 'i';
    let vowel = |c: char| matches!(c, 'a' | 'e' | 'i' | 'o' | 'u');
    let mut out: Vec<char> = Vec::with_capacity(chars.len());
    let mut i = 0_usize;
    while i < chars.len() {
        let (c, next) = (at(i), at(i.saturating_add(1)));
        let (sound, used) = match c {
            'c' if next == 'h' => ('k', 2),
            'c' if next == 'i' && vowel(at(i.saturating_add(2))) => ('c', 2),
            'c' if soft(next) => ('c', 1),
            'c' | 'k' | 'q' => ('k', 1),
            'g' if next == 'h' => ('g', 2),
            'g' if next == 'n' => ('n', 2),
            'g' if next == 'l' && at(i.saturating_add(2)) == 'i' => ('l', 2),
            'g' if next == 'i' && vowel(at(i.saturating_add(2))) => ('j', 2),
            'g' if soft(next) => ('j', 1),
            's' if next == 'c' && soft(at(i.saturating_add(2))) => ('S', 2),
            'p' if next == 'h' => ('f', 2),
            'h' => ('\0', 1),
            'y' => ('i', 1),
            'w' => ('v', 1),
            other => (other, 1),
        };
        if sound != '\0' && out.last() != Some(&sound) {
            out.push(sound);
        }
        i = i.saturating_add(used);
    }
    out.into_iter().collect()
}

#[allow(clippy::cast_precision_loss)]
fn jaro_winkler(a: &[char], b: &[char]) -> f64 {
    if a.is_empty() || b.is_empty() {
        return if a == b { 1.0 } else { 0.0 };
    }
    let reach = (a.len().max(b.len()) / 2).saturating_sub(1);
    let mut b_used = vec![false; b.len()];
    let mut a_match: Vec<char> = Vec::new();
    for (i, ca) in a.iter().enumerate() {
        let lo = i.saturating_sub(reach);
        let hi = i.saturating_add(reach).saturating_add(1).min(b.len());
        for j in lo..hi {
            if b_used.get(j) == Some(&false) && b.get(j) == Some(ca) {
                if let Some(slot) = b_used.get_mut(j) {
                    *slot = true;
                }
                a_match.push(*ca);
                break;
            }
        }
    }
    if a_match.is_empty() {
        return 0.0;
    }
    let b_match: Vec<char> = b
        .iter()
        .zip(&b_used)
        .filter_map(|(c, used)| used.then_some(*c))
        .collect();
    let swaps = a_match.iter().zip(&b_match).filter(|(x, y)| x != y).count() / 2;
    let m = a_match.len() as f64;
    let jaro = (m / a.len() as f64 + m / b.len() as f64 + (m - swaps as f64) / m) / 3.0;
    let prefix = a.iter().zip(b).take(4).take_while(|(x, y)| x == y).count() as f64;
    jaro + prefix * 0.1 * (1.0 - jaro)
}

#[allow(clippy::cast_precision_loss)]
fn edit_similarity(a: &[char], b: &[char]) -> f64 {
    let longest = a.len().max(b.len());
    if longest == 0 {
        return 1.0;
    }
    let mut prev: Vec<usize> = (0..=b.len()).collect();
    for (i, ca) in a.iter().enumerate() {
        let mut row = vec![i.saturating_add(1); b.len().saturating_add(1)];
        for (j, cb) in b.iter().enumerate() {
            let cost = usize::from(ca != cb);
            let del = prev
                .get(j.saturating_add(1))
                .copied()
                .unwrap_or(usize::MAX)
                .saturating_add(1);
            let ins = row.get(j).copied().unwrap_or(usize::MAX).saturating_add(1);
            let sub = prev
                .get(j)
                .copied()
                .unwrap_or(usize::MAX)
                .saturating_add(cost);
            if let Some(cell) = row.get_mut(j.saturating_add(1)) {
                *cell = del.min(ins).min(sub);
            }
        }
        prev = row;
    }
    1.0 - prev.last().copied().unwrap_or(longest) as f64 / longest as f64
}

#[must_use]
pub fn similarity(heard: &str, term: &str) -> f64 {
    let (ka, kb): (Vec<char>, Vec<char>) = (
        phonetic(heard).chars().collect(),
        phonetic(term).chars().collect(),
    );
    let (fa, fb): (Vec<char>, Vec<char>) =
        (fold(heard).chars().collect(), fold(term).chars().collect());
    KEY_SHARE * jaro_winkler(&ka, &kb) + (1.0 - KEY_SHARE) * edit_similarity(&fa, &fb)
}

fn needed(prob: f64, key_len: usize, context: bool) -> f64 {
    let base = if prob < 0.5 {
        0.85
    } else if prob < 0.8 {
        0.9
    } else {
        0.96
    };
    let short = if key_len < 5 { 0.06 } else { 0.0 };
    let bonus = if context { CONTEXT_BONUS } else { 0.0 };
    (base + short - bonus).min(0.99)
}

fn core(text: &str) -> &str {
    text.trim_matches(|c: char| !c.is_alphanumeric())
}

fn split_edges(text: &str) -> (&str, &str, &str) {
    let start = text
        .find(|c: char| c.is_alphanumeric())
        .unwrap_or(text.len());
    let end = text
        .char_indices()
        .rev()
        .find(|(_, c)| c.is_alphanumeric())
        .map_or(start, |(i, c)| i.saturating_add(c.len_utf8()));
    (
        text.get(..start).unwrap_or(""),
        text.get(start..end).unwrap_or(""),
        text.get(end..).unwrap_or(""),
    )
}

impl Lexicon {
    #[must_use]
    pub fn new(terms: &[String]) -> Self {
        let mut seen = HashSet::new();
        let mut list = Vec::new();
        for raw in terms.iter().take(MAX_TERMS) {
            let text: String = raw.split_whitespace().collect::<Vec<_>>().join(" ");
            let folded = fold(&text);
            let key = phonetic(&text);
            if text.chars().count() > MAX_TERM_CHARS
                || key.len() < MIN_KEY
                || !seen.insert(folded.clone())
            {
                continue;
            }
            let words = folded.split(' ').count();
            if words <= MAX_SPAN {
                list.push(Term {
                    text,
                    folded,
                    key,
                    words,
                });
            }
        }
        let known = list
            .iter()
            .flat_map(|t| t.folded.split(' ').map(str::to_owned).collect::<Vec<_>>())
            .collect();
        Self { terms: list, known }
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.terms.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.terms.is_empty()
    }

    fn best(&self, heard: &str, words: usize) -> Option<(&Term, f64)> {
        let key_len = phonetic(heard).len();
        if key_len < MIN_KEY {
            return None;
        }
        self.terms
            .iter()
            .filter(|t| t.words == words)
            .map(|t| (t, similarity(heard, &t.text)))
            .max_by(|a, b| a.1.total_cmp(&b.1))
    }

    #[must_use]
    pub fn correct<S: BuildHasher>(
        &self,
        tokens: &[Token],
        context: &HashSet<String, S>,
    ) -> (String, Vec<Correction>) {
        let tokens = tokens
            .get(..tokens.len().min(MAX_TOKENS))
            .unwrap_or_default();
        let mut out = String::new();
        let mut fixes = Vec::new();
        let mut i = 0_usize;
        while i < tokens.len() {
            let mut taken = 0_usize;
            for span in (1..=MAX_SPAN).rev() {
                let Some(window) = tokens.get(i..i.saturating_add(span)) else {
                    continue;
                };
                if window.iter().any(|t| core(&t.text).is_empty()) {
                    continue;
                }
                let heard = window
                    .iter()
                    .map(|t| core(&t.text))
                    .collect::<Vec<_>>()
                    .join(" ");
                let folded = fold(&heard);
                let Some((term, score)) = self.best(&heard, span) else {
                    continue;
                };
                let exact = term.folded == folded;
                if !exact && span == 1 && self.known.contains(&folded) {
                    break;
                }
                #[allow(clippy::cast_precision_loss)]
                let prob = window.iter().map(|t| t.prob).sum::<f64>() / span as f64;
                let in_context = context.contains(&term.folded);
                if exact && heard == term.text {
                    break;
                }
                if exact
                    || score >= needed(prob, term.key.len().min(phonetic(&heard).len()), in_context)
                {
                    let first = window.first().map_or("", |t| t.text.as_str());
                    let last = window.last().map_or("", |t| t.text.as_str());
                    let (lead, _, _) = split_edges(first);
                    let (_, _, tail) = split_edges(last);
                    out.push_str(lead);
                    out.push_str(&term.text);
                    out.push_str(tail);
                    fixes.push(Correction {
                        heard,
                        term: term.text.clone(),
                        score,
                    });
                    taken = span;
                    break;
                }
            }
            if taken == 0 {
                if let Some(t) = tokens.get(i) {
                    out.push_str(&t.text);
                }
                taken = 1;
            }
            i = i.saturating_add(taken);
        }
        (out, fixes)
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct Segment {
    pub text: String,
    pub avg_logprob: f64,
    pub no_speech_prob: f64,
    pub compression_ratio: f64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Assessment {
    pub keep: Vec<bool>,
    pub reasons: Vec<&'static str>,
    pub confidence: f64,
}

fn looping(text: &str) -> bool {
    let words: Vec<String> = fold(text).split(' ').map(str::to_owned).collect();
    for size in 1..=4_usize {
        let needed = if size == 1 { 5 } else { 3 };
        let span = size.saturating_mul(needed);
        if words.len() < span {
            continue;
        }
        for start in 0..=words.len().saturating_sub(span) {
            let Some(first) = words.get(start..start.saturating_add(size)) else {
                continue;
            };
            let repeats = (1..needed).all(|k| {
                let at = start.saturating_add(k.saturating_mul(size));
                words.get(at..at.saturating_add(size)) == Some(first)
            });
            if repeats {
                return true;
            }
        }
    }
    false
}

#[must_use]
pub fn assess<S: BuildHasher>(
    segments: &[Segment],
    prompt: &str,
    phrases: &HashSet<String, S>,
) -> Assessment {
    let prompt = fold(prompt);
    let mut keep = Vec::with_capacity(segments.len());
    let mut reasons = Vec::with_capacity(segments.len());
    let mut kept = Vec::new();
    for s in segments {
        let folded = fold(&s.text);
        let finite = s.avg_logprob.is_finite()
            && s.no_speech_prob.is_finite()
            && s.compression_ratio.is_finite();
        let reason = if folded.is_empty() {
            "vuoto"
        } else if !finite {
            "valori non validi"
        } else if s.no_speech_prob > 0.6 && s.avg_logprob < -1.0 {
            "silenzio"
        } else if s.compression_ratio > 2.4 || looping(&s.text) {
            "ripetizione"
        } else if phrases.contains(&folded) {
            "frase tipica di rumore"
        } else if !prompt.is_empty() && prompt.contains(&folded) && s.avg_logprob < -0.5 {
            "copia del suggerimento"
        } else {
            ""
        };
        keep.push(reason.is_empty());
        reasons.push(reason);
        if reason.is_empty() {
            kept.push(s.avg_logprob.min(0.0).exp());
        }
    }
    #[allow(clippy::cast_precision_loss)]
    let confidence = if kept.is_empty() {
        0.0
    } else {
        kept.iter().sum::<f64>() / kept.len() as f64
    };
    Assessment {
        keep,
        reasons,
        confidence,
    }
}
