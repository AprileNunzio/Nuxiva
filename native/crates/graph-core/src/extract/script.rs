use super::util::{after, clip, ident, line_no, quoted, strip_all};
use crate::model::{Fact, Facts, SymKind};
use crate::settings::GraphSettings;

const MARKERS: [&str; 4] = [" from ", "require(", "import(", "import "];

fn specifiers(line: &str) -> Vec<&str> {
    let mut found = Vec::new();
    for marker in MARKERS {
        let mut cursor = 0usize;
        while let Some(pos) = line.get(cursor..).and_then(|t| t.find(marker)) {
            let start = cursor.saturating_add(pos).saturating_add(marker.len());
            if let Some(spec) = line.get(start..).and_then(quoted) {
                if !found.contains(&spec) {
                    found.push(spec);
                }
            }
            cursor = start;
        }
    }
    found
}

fn symbol(line: &str) -> Option<(SymKind, String)> {
    let exported = after(line, "export").is_some();
    let rest = strip_all(line, &["export", "default", "async", "declare", "abstract"]);
    if let Some(r) = after(rest, "function") {
        let name = ident(r.trim_start_matches('*').trim_start());
        return (!name.is_empty()).then(|| (SymKind::Function, name.to_owned()));
    }
    let table = [
        ("class", SymKind::Type),
        ("interface", SymKind::Type),
        ("type", SymKind::Type),
        ("enum", SymKind::Type),
    ];
    for (word, kind) in table {
        if let Some(r) = after(rest, word) {
            let name = ident(r);
            if !name.is_empty() {
                return Some((kind, name.to_owned()));
            }
        }
    }
    if exported {
        for word in ["const", "let", "var"] {
            if let Some(r) = after(rest, word) {
                let name = ident(r);
                if !name.is_empty() {
                    return Some((SymKind::Constant, name.to_owned()));
                }
            }
        }
    }
    None
}

#[must_use]
pub fn extract(text: &str, settings: &GraphSettings) -> Facts {
    let mut facts = Facts::default();
    for (index, raw) in text.lines().enumerate() {
        let line = raw.trim();
        if line.starts_with("//")
            || line.starts_with('*')
            || line.starts_with("/*")
            || line.is_empty()
        {
            continue;
        }
        for spec in specifiers(line) {
            if facts.imports.len() < settings.max_imports_per_file {
                facts.imports.push(format!("js:{spec}"));
            }
        }
        if raw.starts_with(char::is_whitespace)
            || facts.symbols.len() >= settings.max_symbols_per_file
        {
            continue;
        }
        if let Some((kind, name)) = symbol(line) {
            facts.symbols.push(Fact {
                name: clip(&name, settings.max_name_chars),
                kind,
                line: line_no(index),
            });
        }
    }
    facts
}
