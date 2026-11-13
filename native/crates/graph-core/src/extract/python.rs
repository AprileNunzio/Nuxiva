use super::util::{after, clip, ident, line_no};
use crate::model::{Fact, Facts, SymKind};
use crate::settings::GraphSettings;

fn push(facts: &mut Facts, value: String, settings: &GraphSettings) {
    if facts.imports.len() < settings.max_imports_per_file && !facts.imports.contains(&value) {
        facts.imports.push(value);
    }
}

fn dotted(text: &str) -> &str {
    let end = text
        .char_indices()
        .find(|(_, c)| !(c.is_alphanumeric() || *c == '_' || *c == '.'))
        .map_or(text.len(), |(i, _)| i);
    text.get(..end).unwrap_or("")
}

fn constant(line: &str) -> Option<&str> {
    let name = ident(line);
    let tail = line.get(name.len()..)?.trim_start();
    let upper = name.len() > 1
        && name
            .chars()
            .all(|c| c.is_ascii_uppercase() || c.is_ascii_digit() || c == '_');
    (upper && tail.starts_with('=') && !tail.starts_with("==")).then_some(name)
}

#[must_use]
pub fn extract(text: &str, settings: &GraphSettings) -> Facts {
    let mut facts = Facts::default();
    for (index, raw) in text.lines().enumerate() {
        if raw.starts_with(char::is_whitespace) || raw.starts_with('#') || raw.is_empty() {
            continue;
        }
        let line = raw.trim_end();
        if let Some(rest) = after(line, "import") {
            for part in rest.split(',') {
                let name = dotted(part.trim());
                if !name.is_empty() {
                    push(&mut facts, format!("py:{name}"), settings);
                }
            }
            continue;
        }
        if let Some(rest) = after(line, "from") {
            let module = dotted(rest);
            let tail = rest.get(module.len()..).unwrap_or("").trim_start();
            if let Some(names) = after(tail, "import") {
                let names = names.trim_start_matches('(');
                for item in names.split(',') {
                    let name = ident(item.trim());
                    if !name.is_empty() && name != "as" {
                        let sep = if module.ends_with('.') { "" } else { "." };
                        push(&mut facts, format!("py:{module}{sep}{name}"), settings);
                    }
                }
            }
            if !module.is_empty() {
                push(&mut facts, format!("py:{module}"), settings);
            }
            continue;
        }
        if facts.symbols.len() >= settings.max_symbols_per_file {
            continue;
        }
        let stripped = after(line, "async").unwrap_or(line);
        let found = after(stripped, "def")
            .map(|r| (SymKind::Function, ident(r)))
            .or_else(|| after(stripped, "class").map(|r| (SymKind::Type, ident(r))))
            .or_else(|| constant(line).map(|n| (SymKind::Constant, n)));
        if let Some((kind, name)) = found.filter(|(_, n)| !n.is_empty()) {
            facts.symbols.push(Fact {
                name: clip(name, settings.max_name_chars),
                kind,
                line: line_no(index),
            });
        }
    }
    facts
}
