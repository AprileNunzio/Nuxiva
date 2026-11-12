use serde::{Deserialize, Serialize};

use crate::kind::{Kind, Level, REQUIRED_KEYS, SCHEMA};

pub const MAX_KEY: usize = 32;
pub const MAX_VALUE: usize = 512;
pub const MAX_KEYS: usize = 32;
pub const MAX_HEADING: usize = 160;
pub const MAX_SECTION: usize = 64 * 1024;
pub const MAX_SECTIONS: usize = 64;
pub const MAX_DOC: usize = 256 * 1024;

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Section {
    pub anchor: String,
    pub heading: String,
    pub body: String,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Doc {
    pub front: Vec<(String, String)>,
    pub title: String,
    pub sections: Vec<Section>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Problem {
    pub at: String,
    pub code: String,
}

impl Problem {
    #[must_use]
    pub fn new(at: &str, code: &str) -> Self {
        Self {
            at: at.to_owned(),
            code: code.to_owned(),
        }
    }
}

#[must_use]
pub fn valid_key(key: &str) -> bool {
    !key.is_empty()
        && key.len() <= MAX_KEY
        && key.bytes().all(|b| b.is_ascii_lowercase() || b == b'_')
}

fn clip(text: &str, limit: usize) -> String {
    text.chars().take(limit).collect()
}

#[must_use]
pub fn line(text: &str, limit: usize) -> String {
    let flat: String = text
        .chars()
        .map(|c| if c.is_control() { ' ' } else { c })
        .collect();
    clip(flat.trim(), limit)
}

#[must_use]
pub fn body(text: &str) -> String {
    let clean: String = text
        .chars()
        .filter(|c| *c == '\n' || *c == '\t' || !c.is_control())
        .collect();
    let safe = clean.replace("<!--", "&lt;!--");
    clip(safe.trim_matches('\n'), MAX_SECTION)
}

#[must_use]
pub fn sanitize(doc: &Doc) -> Doc {
    Doc {
        front: doc
            .front
            .iter()
            .filter(|(k, _)| valid_key(k))
            .take(MAX_KEYS)
            .map(|(k, v)| (k.clone(), line(v, MAX_VALUE)))
            .collect(),
        title: line(&doc.title, MAX_HEADING),
        sections: doc
            .sections
            .iter()
            .filter(|s| valid_key(&s.anchor))
            .take(MAX_SECTIONS)
            .map(|s| Section {
                anchor: s.anchor.clone(),
                heading: line(&s.heading, MAX_HEADING),
                body: body(&s.body),
            })
            .collect(),
    }
}

#[must_use]
pub fn render(doc: &Doc) -> String {
    let doc = sanitize(doc);
    let mut out = String::from("---\n");
    for (k, v) in &doc.front {
        out.push_str(k);
        out.push_str(": ");
        out.push_str(v);
        out.push('\n');
    }
    out.push_str("---\n\n# ");
    out.push_str(&doc.title);
    out.push('\n');
    for s in &doc.sections {
        out.push_str("\n<!-- s:");
        out.push_str(&s.anchor);
        out.push_str(" -->\n## ");
        out.push_str(&s.heading);
        out.push('\n');
        if !s.body.is_empty() {
            out.push_str(&s.body);
            out.push('\n');
        }
    }
    out
}

fn anchor_of(line: &str) -> Option<&str> {
    line.strip_prefix("<!-- s:")
        .and_then(|rest| rest.strip_suffix(" -->"))
        .filter(|a| valid_key(a))
}

pub fn parse(text: &str) -> Result<Doc, Problem> {
    if text.len() > MAX_DOC {
        return Err(Problem::new("", "too_large"));
    }
    let rest = text
        .strip_prefix("---\n")
        .ok_or_else(|| Problem::new("", "no_front"))?;
    let (front_text, rest) = match rest.strip_prefix("---\n") {
        Some(after) => ("", after),
        None => rest
            .split_once("\n---\n")
            .ok_or_else(|| Problem::new("", "no_front_end"))?,
    };
    let mut front = Vec::new();
    for raw in front_text.lines() {
        let (k, v) = raw
            .split_once(": ")
            .ok_or_else(|| Problem::new("front", "bad_line"))?;
        if !valid_key(k) {
            return Err(Problem::new("front", "bad_key"));
        }
        front.push((k.to_owned(), v.to_owned()));
    }
    let rest = rest
        .strip_prefix("\n# ")
        .ok_or_else(|| Problem::new("", "no_title"))?;
    let mut lines = rest.split('\n');
    let title = lines.next().unwrap_or("").to_owned();
    let mut sections: Vec<Section> = Vec::new();
    let mut current: Option<Section> = None;
    let mut expect_heading = false;
    for raw in lines {
        if expect_heading {
            let heading = raw
                .strip_prefix("## ")
                .ok_or_else(|| Problem::new("section", "no_heading"))?;
            if let Some(s) = current.as_mut() {
                heading.clone_into(&mut s.heading);
            }
            expect_heading = false;
            continue;
        }
        if let Some(anchor) = anchor_of(raw) {
            if let Some(mut done) = current.take() {
                done.body = done.body.trim_matches('\n').to_string();
                sections.push(done);
            }
            current = Some(Section {
                anchor: anchor.to_owned(),
                ..Section::default()
            });
            expect_heading = true;
            continue;
        }
        match current.as_mut() {
            Some(s) => {
                s.body.push_str(raw);
                s.body.push('\n');
            }
            None if raw.is_empty() => {}
            None => return Err(Problem::new("", "text_outside_section")),
        }
    }
    if expect_heading {
        return Err(Problem::new("section", "no_heading"));
    }
    if let Some(mut done) = current.take() {
        done.body = done.body.trim_matches('\n').to_string();
        sections.push(done);
    }
    Ok(Doc {
        front,
        title,
        sections,
    })
}

#[must_use]
pub fn get<'a>(doc: &'a Doc, key: &str) -> Option<&'a str> {
    doc.front
        .iter()
        .find(|(k, _)| k == key)
        .map(|(_, v)| v.as_str())
}

#[must_use]
pub fn validate(doc: &Doc, kind: Kind) -> Vec<Problem> {
    let mut out = Vec::new();
    for key in REQUIRED_KEYS {
        if get(doc, key).is_none_or(str::is_empty) {
            out.push(Problem::new(key, "missing"));
        }
    }
    if get(doc, "schema").is_some_and(|v| v != SCHEMA) {
        out.push(Problem::new("schema", "unknown_schema"));
    }
    if get(doc, "file").is_some_and(|v| v != kind.as_str()) {
        out.push(Problem::new("file", "wrong_kind"));
    }
    if get(doc, "livello").is_some_and(|v| Level::parse(v).is_none()) {
        out.push(Problem::new("livello", "unknown_level"));
    }
    let mut seen: Vec<&str> = Vec::new();
    for s in &doc.sections {
        if seen.contains(&s.anchor.as_str()) {
            out.push(Problem::new(&s.anchor, "duplicate"));
        }
        seen.push(&s.anchor);
    }
    for anchor in kind.sections() {
        if !seen.contains(anchor) {
            out.push(Problem::new(anchor, "missing_section"));
        }
    }
    if doc.title.trim().is_empty() {
        out.push(Problem::new("title", "missing"));
    }
    out
}
