use std::collections::BTreeMap;

use zeroize::Zeroize;

use crate::envelope::{MAX_FIELDS, MAX_KEY, MAX_TEXT, MAX_TOKEN, Scalar, is_hex, is_token};

const DENIED: &[&str] = &[
    "name",
    "nome",
    "voice",
    "voce",
    "face",
    "volto",
    "allerg",
    "email",
    "mail",
    "phone",
    "telefono",
    "address",
    "indirizzo",
    "passw",
    "secret",
    "token",
    "apikey",
    "api_key",
    "transcript",
    "trascri",
    "utterance",
    "frase",
    "prompt",
    "body",
    "text",
    "speech",
    "embedding",
    "vector",
    "biometric",
    "health",
    "salute",
    "diagnos",
    "medic",
    "birth",
    "nascita",
    "fiscal",
    "iban",
    "card",
    "cookie",
    "credential",
    "bearer",
];
const TEXT_KEYS: &[&str] = &["msg", "error", "detail", "reason"];
const REDACTED: &str = "[redatto]";

pub struct Redactor {
    key: [u8; 32],
}

impl std::fmt::Debug for Redactor {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("Redactor")
    }
}

impl Drop for Redactor {
    fn drop(&mut self) {
        self.key.zeroize();
    }
}

fn denied(key: &str) -> bool {
    DENIED.iter().any(|d| key.contains(d))
}

fn digits_run(chars: &[char], start: usize) -> usize {
    let mut end = start;
    while chars
        .get(end)
        .is_some_and(|c| c.is_ascii_digit() || matches!(c, '-' | ' ' | '.' | '+'))
    {
        end = end.saturating_add(1);
    }
    end
}

impl Redactor {
    #[must_use]
    pub fn new(key: [u8; 32]) -> Self {
        Self { key }
    }

    #[must_use]
    pub fn anon(&self, scope: &str, value: &str) -> String {
        let mut hasher = blake3::Hasher::new_keyed(&self.key);
        hasher.update(b"nuxiva.collaudo.anon:");
        hasher.update(scope.as_bytes());
        hasher.update(&[0]);
        hasher.update(value.as_bytes());
        let hex = hasher.finalize().to_hex();
        format!("a:{}", hex.as_str().get(..16).unwrap_or_default())
    }

    fn pseudonym(&self, key: &str, value: &str) -> String {
        let mut hasher = blake3::Hasher::new_keyed(&self.key);
        hasher.update(b"nuxiva.collaudo.value:");
        hasher.update(key.as_bytes());
        hasher.update(&[0]);
        hasher.update(value.as_bytes());
        let hex = hasher.finalize().to_hex();
        format!("h:{}", hex.as_str().get(..12).unwrap_or_default())
    }

    #[must_use]
    pub fn scrub_text(value: &str) -> String {
        let flat: Vec<char> = value
            .chars()
            .map(|c| if c.is_control() { ' ' } else { c })
            .collect();
        let mut out = String::with_capacity(flat.len());
        let mut i = 0usize;
        while let Some(&c) = flat.get(i) {
            if c == '/' {
                let rest: String = flat.iter().skip(i).take(8).collect();
                if rest.starts_with("/home/") || rest.starts_with("/Users/") {
                    let skip = if rest.starts_with("/home/") { 6 } else { 7 };
                    out.push_str(&rest.chars().take(skip).collect::<String>());
                    out.push('~');
                    i = i.saturating_add(skip);
                    while flat
                        .get(i)
                        .is_some_and(|c| !matches!(c, '/' | ' ' | '"' | '\''))
                    {
                        i = i.saturating_add(1);
                    }
                    continue;
                }
            }
            if c.is_ascii_digit() || c == '+' {
                let mut end = digits_run(&flat, i);
                while end > i.saturating_add(1)
                    && !flat
                        .get(end.saturating_sub(1))
                        .is_some_and(char::is_ascii_digit)
                {
                    end = end.saturating_sub(1);
                }
                let slice: String = flat.iter().skip(i).take(end.saturating_sub(i)).collect();
                let digits = slice.chars().filter(char::is_ascii_digit).count();
                if digits >= 7 {
                    out.push_str(REDACTED);
                    i = end;
                    continue;
                }
            }
            out.push(c);
            i = i.saturating_add(1);
        }
        let mut words: Vec<String> = Vec::new();
        for word in out.split(' ') {
            let bare = word.trim_matches(|c: char| {
                !c.is_ascii_alphanumeric() && !matches!(c, '@' | '.' | '_' | '-' | '+' | '/' | '=')
            });
            let is_email = bare.contains('@') && bare.contains('.');
            let is_hex_blob = bare.len() >= 24 && bare.bytes().all(|b| b.is_ascii_hexdigit());
            let is_long_blob = bare.len() >= 32
                && bare.bytes().all(|b| {
                    b.is_ascii_alphanumeric() || matches!(b, b'+' | b'/' | b'=' | b'-' | b'_')
                });
            if is_email || is_hex_blob || is_long_blob {
                words.push(REDACTED.to_owned());
            } else {
                words.push(word.to_owned());
            }
        }
        words.join(" ").chars().take(MAX_TEXT).collect()
    }

    fn text_value(&self, key: &str, value: &str, allow_free: bool) -> (Scalar, bool) {
        if denied(key) {
            return (Scalar::Text(REDACTED.to_owned()), true);
        }
        if key.ends_with("_ref") {
            return (Scalar::Text(self.pseudonym(key, value)), true);
        }
        if allow_free && TEXT_KEYS.contains(&key) {
            let scrubbed = Self::scrub_text(value);
            let changed = scrubbed != value;
            return (Scalar::Text(scrubbed), changed);
        }
        let looks_pii =
            value.contains('@') || (value.bytes().filter(u8::is_ascii_digit).count() >= 7);
        if is_token(value, MAX_TOKEN) && !looks_pii && !is_hex(value, 24, usize::MAX) {
            return (Scalar::Text(value.to_owned()), false);
        }
        (Scalar::Text(self.pseudonym(key, value)), true)
    }

    #[must_use]
    pub fn fields(
        &self,
        raw: BTreeMap<String, Scalar>,
        allow_free_text: bool,
    ) -> BTreeMap<String, Scalar> {
        let mut out = BTreeMap::new();
        let mut redacted: i64 = 0;
        for (key, value) in raw {
            let key = key.trim().to_ascii_lowercase();
            if out.len() >= MAX_FIELDS.saturating_sub(1) {
                redacted = redacted.saturating_add(1);
                continue;
            }
            if !is_token(&key, MAX_KEY) {
                redacted = redacted.saturating_add(1);
                continue;
            }
            let value = match value {
                Scalar::Text(t) => {
                    let (v, changed) = self.text_value(&key, &t, allow_free_text);
                    if changed {
                        redacted = redacted.saturating_add(1);
                    }
                    v
                }
                Scalar::Float(f) if !f.is_finite() => {
                    redacted = redacted.saturating_add(1);
                    continue;
                }
                other => other,
            };
            out.insert(key, value);
        }
        if redacted > 0 {
            out.insert("redacted_n".to_owned(), Scalar::Int(redacted));
        }
        out
    }
}
