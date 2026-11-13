use serde::{Deserialize, Serialize};
use std::fmt;

pub const DIR: &str = "changelog";
pub const MAX_FILE_BYTES: usize = 16 * 1024;
pub const MAX_FILES: usize = 60;
pub const MAX_TITLE: usize = 140;
pub const MAX_ITEM: usize = 320;
pub const MAX_ITEMS: usize = 24;
const MAX_NAME: usize = 96;
const INVISIBLE: [(u32, u32); 6] = [
    (0x200B, 0x200F),
    (0x202A, 0x202E),
    (0x2060, 0x2064),
    (0x2066, 0x2069),
    (0xFEFF, 0xFEFF),
    (0xFFF9, 0xFFFB),
];

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NoteError {
    Name,
    TooLarge,
    Malformed,
    Schema,
    Date,
    Empty,
    TooMany,
    Text,
}

impl NoteError {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Name => "name",
            Self::TooLarge => "too_large",
            Self::Malformed => "malformed",
            Self::Schema => "schema",
            Self::Date => "date",
            Self::Empty => "empty",
            Self::TooMany => "too_many",
            Self::Text => "text",
        }
    }
}

impl fmt::Display for NoteError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.code())
    }
}

impl std::error::Error for NoteError {}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Text {
    pub it: String,
    pub en: String,
    pub fr: String,
    pub es: String,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawNote {
    schema: u8,
    date: String,
    title: Text,
    #[serde(default)]
    features: Vec<Text>,
    #[serde(default)]
    fixes: Vec<Text>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct ReleaseNote {
    pub id: String,
    pub date: String,
    pub title: Text,
    pub features: Vec<Text>,
    pub fixes: Vec<Text>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Rejection {
    pub file: String,
    pub reason: &'static str,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize)]
pub struct Digest {
    pub notes: Vec<ReleaseNote>,
    pub features: usize,
    pub fixes: usize,
    pub rejected: Vec<Rejection>,
}

#[must_use]
pub fn valid_name(name: &str) -> bool {
    let Some(stem) = name.strip_suffix(".json") else {
        return false;
    };
    let Some((stamp, slug)) = stem.split_once('-') else {
        return false;
    };
    name.len() <= MAX_NAME
        && stamp.len() == 14
        && stamp.bytes().all(|b| b.is_ascii_digit())
        && !slug.is_empty()
        && slug.split('-').all(|part| {
            !part.is_empty()
                && part
                    .bytes()
                    .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit())
        })
}

fn invisible(c: char) -> bool {
    let code = u32::from(c);
    INVISIBLE.iter().any(|&(lo, hi)| (lo..=hi).contains(&code))
}

fn clean(text: &str, limit: usize) -> Result<String, NoteError> {
    if text.chars().any(|c| c.is_control() || invisible(c)) {
        return Err(NoteError::Text);
    }
    let trimmed = text.trim();
    if trimmed.is_empty() || trimmed.chars().count() > limit {
        return Err(NoteError::Text);
    }
    Ok(trimmed.to_owned())
}

fn clean_text(text: &Text, limit: usize) -> Result<Text, NoteError> {
    Ok(Text {
        it: clean(&text.it, limit)?,
        en: clean(&text.en, limit)?,
        fr: clean(&text.fr, limit)?,
        es: clean(&text.es, limit)?,
    })
}

fn clean_items(items: &[Text]) -> Result<Vec<Text>, NoteError> {
    if items.len() > MAX_ITEMS {
        return Err(NoteError::TooMany);
    }
    items
        .iter()
        .map(|item| clean_text(item, MAX_ITEM))
        .collect()
}

fn valid_date(date: &str, stamp: &str) -> bool {
    let bytes = date.as_bytes();
    let shape = bytes.len() == 10
        && bytes.get(4) == Some(&b'-')
        && bytes.get(7) == Some(&b'-')
        && bytes
            .iter()
            .enumerate()
            .all(|(i, b)| i == 4 || i == 7 || b.is_ascii_digit());
    if !shape {
        return false;
    }
    let number =
        |range: std::ops::Range<usize>| date.get(range).and_then(|s| s.parse::<u32>().ok());
    let month = number(5..7).unwrap_or(0);
    let day = number(8..10).unwrap_or(0);
    (1..=12).contains(&month)
        && (1..=31).contains(&day)
        && date.replace('-', "") == stamp.get(..8).unwrap_or("")
}

pub fn parse(name: &str, raw: &str) -> Result<ReleaseNote, NoteError> {
    if !valid_name(name) {
        return Err(NoteError::Name);
    }
    if raw.len() > MAX_FILE_BYTES {
        return Err(NoteError::TooLarge);
    }
    let note: RawNote = serde_json::from_str(raw).map_err(|_| NoteError::Malformed)?;
    if note.schema != 1 {
        return Err(NoteError::Schema);
    }
    let id = name.trim_end_matches(".json").to_owned();
    if !valid_date(&note.date, &id) {
        return Err(NoteError::Date);
    }
    if note.features.is_empty() && note.fixes.is_empty() {
        return Err(NoteError::Empty);
    }
    Ok(ReleaseNote {
        id,
        date: note.date,
        title: clean_text(&note.title, MAX_TITLE)?,
        features: clean_items(&note.features)?,
        fixes: clean_items(&note.fixes)?,
    })
}

#[must_use]
pub fn digest(files: &[(String, String)]) -> Digest {
    let mut out = Digest::default();
    for (name, raw) in files {
        match parse(name, raw) {
            Ok(note) => out.notes.push(note),
            Err(err) => out.rejected.push(Rejection {
                file: if valid_name(name) {
                    name.clone()
                } else {
                    String::new()
                },
                reason: err.code(),
            }),
        }
    }
    out.notes.sort_by(|a, b| b.id.cmp(&a.id));
    out.notes.dedup_by(|a, b| a.id == b.id);
    out.notes.truncate(MAX_FILES);
    out.features = out.notes.iter().map(|n| n.features.len()).sum();
    out.fixes = out.notes.iter().map(|n| n.fixes.len()).sum();
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    const GOOD: &str = r#"{"schema":1,"date":"2026-11-13","title":{"it":"Titolo","en":"Title","fr":"Titre","es":"Título"},"features":[{"it":"Nuovo","en":"New","fr":"Nouveau","es":"Nuevo"}],"fixes":[]}"#;

    #[test]
    fn accepts_valid_note() {
        let note = parse("20261113053722-novita-aggiornamento.json", GOOD);
        assert_eq!(note.as_ref().map(|n| n.features.len()), Ok(1));
        assert_eq!(
            note.map(|n| n.id),
            Ok("20261113053722-novita-aggiornamento".to_owned())
        );
    }

    #[test]
    fn rejects_bad_names_and_dates() {
        assert_eq!(parse("../evil.json", GOOD), Err(NoteError::Name));
        assert_eq!(parse("20261113053722-Bad.json", GOOD), Err(NoteError::Name));
        assert_eq!(parse("20261114053722-x.json", GOOD), Err(NoteError::Date));
    }

    #[test]
    fn rejects_hostile_text() {
        let bidi = GOOD.replace("Nuovo", "Nu\u{202E}ovo");
        assert_eq!(parse("20261113053722-x.json", &bidi), Err(NoteError::Text));
        let ctrl = GOOD.replace("Nuovo", "Nu\\u0007ovo");
        assert_eq!(parse("20261113053722-x.json", &ctrl), Err(NoteError::Text));
        let extra = GOOD.replace("\"fixes\":[]", "\"fixes\":[],\"html\":\"<b>\"");
        assert_eq!(
            parse("20261113053722-x.json", &extra),
            Err(NoteError::Malformed)
        );
        let empty = GOOD.replace(
            "[{\"it\":\"Nuovo\",\"en\":\"New\",\"fr\":\"Nouveau\",\"es\":\"Nuevo\"}]",
            "[]",
        );
        assert_eq!(
            parse("20261113053722-x.json", &empty),
            Err(NoteError::Empty)
        );
        let big = " ".repeat(MAX_FILE_BYTES + 1);
        assert_eq!(
            parse("20261113053722-x.json", &big),
            Err(NoteError::TooLarge)
        );
    }

    #[test]
    fn digest_sorts_newest_first_and_counts() {
        let older = GOOD.replace("2026-11-13", "2026-11-12");
        let files = vec![
            ("20261112000000-a.json".to_owned(), older),
            ("20261113000000-b.json".to_owned(), GOOD.to_owned()),
            ("bad".to_owned(), GOOD.to_owned()),
        ];
        let out = digest(&files);
        assert_eq!(
            out.notes.first().map(|n| n.id.as_str()),
            Some("20261113000000-b")
        );
        assert_eq!(out.features, 2);
        assert_eq!(out.rejected.len(), 1);
    }
}
