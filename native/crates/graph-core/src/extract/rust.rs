use super::util::{after, clip, ident, line_no, strip_all};
use crate::model::{Fact, Facts, SymKind};
use crate::settings::GraphSettings;

const QUALIFIERS: [&str; 6] = ["pub", "async", "unsafe", "extern", "default", "mut"];
const MAX_DEPTH: usize = 6;

fn expand(path: &str, out: &mut Vec<String>, depth: usize) {
    let path = path.trim();
    if depth > MAX_DEPTH || out.len() >= 512 {
        return;
    }
    let Some(open) = path.find('{') else {
        let clean = path
            .split(" as ")
            .next()
            .unwrap_or("")
            .trim()
            .trim_end_matches("::*");
        if !clean.is_empty() {
            out.push(clean.to_owned());
        }
        return;
    };
    let prefix = path.get(..open).unwrap_or("");
    let close = path.rfind('}').unwrap_or(path.len());
    let body = path.get(open.saturating_add(1)..close).unwrap_or("");
    let mut level = 0usize;
    let mut start = 0usize;
    let mut parts: Vec<&str> = Vec::new();
    for (i, c) in body.char_indices() {
        match c {
            '{' => level = level.saturating_add(1),
            '}' => level = level.saturating_sub(1),
            ',' if level == 0 => {
                parts.push(body.get(start..i).unwrap_or(""));
                start = i.saturating_add(1);
            }
            _ => {}
        }
    }
    parts.push(body.get(start..).unwrap_or(""));
    for part in parts {
        let part = part.trim();
        if part.is_empty() {
            continue;
        }
        if part == "self" {
            out.push(prefix.trim_end_matches("::").to_owned());
        } else {
            expand(&format!("{prefix}{part}"), out, depth.saturating_add(1));
        }
    }
}

fn symbol(line: &str) -> Option<(SymKind, String)> {
    let rest = strip_all(line, &QUALIFIERS);
    let rest = rest
        .strip_prefix("pub(")
        .and_then(|r| r.split_once(')'))
        .map_or(rest, |(_, r)| r.trim_start());
    let rest = strip_all(rest, &QUALIFIERS);
    let rest = after(rest, "const")
        .filter(|r| {
            ["fn", "unsafe", "async", "extern"]
                .iter()
                .any(|w| after(r, w).is_some())
        })
        .map_or(rest, |r| strip_all(r, &QUALIFIERS));
    let table = [
        ("fn", SymKind::Function),
        ("struct", SymKind::Type),
        ("enum", SymKind::Type),
        ("union", SymKind::Type),
        ("type", SymKind::Type),
        ("trait", SymKind::Trait),
        ("mod", SymKind::Module),
        ("const", SymKind::Constant),
        ("static", SymKind::Constant),
    ];
    for (word, kind) in table {
        if let Some(tail) = after(rest, word) {
            let tail = if word == "static" {
                after(tail, "mut").unwrap_or(tail)
            } else {
                tail
            };
            let name = ident(tail);
            if !name.is_empty() {
                return Some((kind, name.to_owned()));
            }
        }
    }
    None
}

#[must_use]
pub fn extract(text: &str, settings: &GraphSettings) -> Facts {
    let mut facts = Facts::default();
    let mut pending: Option<String> = None;
    for (index, raw) in text.lines().enumerate() {
        let line = raw.trim();
        if let Some(buffer) = pending.as_mut() {
            buffer.push(' ');
            buffer.push_str(line);
            if line.contains(';') {
                let done = pending.take().unwrap_or_default();
                push_use(&done, &mut facts, settings);
            } else if buffer.len() > 4_096 {
                pending = None;
            }
            continue;
        }
        if line.starts_with("//") || line.is_empty() {
            continue;
        }
        let stripped = strip_all(line, &["pub"]);
        let stripped = stripped
            .strip_prefix("pub(")
            .and_then(|r| r.split_once(')'))
            .map_or(stripped, |(_, r)| r.trim_start());
        if let Some(rest) = after(stripped, "use") {
            if rest.contains(';') {
                push_use(rest, &mut facts, settings);
            } else {
                pending = Some(rest.to_owned());
            }
            continue;
        }
        if let Some(rest) = after(stripped, "mod") {
            let name = ident(rest);
            if !name.is_empty()
                && rest
                    .get(name.len()..)
                    .is_some_and(|t| t.trim_start().starts_with(';'))
            {
                push_import(&mut facts, format!("mod:{name}"), settings);
            }
        }
        if raw.starts_with(char::is_whitespace) && !line.starts_with("pub") {
            continue;
        }
        if facts.symbols.len() < settings.max_symbols_per_file {
            if let Some((kind, name)) = symbol(line) {
                facts.symbols.push(Fact {
                    name: clip(&name, settings.max_name_chars),
                    kind,
                    line: line_no(index),
                });
            }
        }
    }
    facts
}

fn push_import(facts: &mut Facts, value: String, settings: &GraphSettings) {
    if facts.imports.len() < settings.max_imports_per_file && !facts.imports.contains(&value) {
        facts.imports.push(value);
    }
}

fn push_use(raw: &str, facts: &mut Facts, settings: &GraphSettings) {
    let body = raw.split(';').next().unwrap_or("");
    let mut out = Vec::new();
    expand(body, &mut out, 0);
    for path in out {
        let clean: String = path.chars().filter(|c| !c.is_whitespace()).collect();
        push_import(
            facts,
            format!("use:{}", clean.trim_start_matches("::")),
            settings,
        );
    }
}
