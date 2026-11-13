use super::util::{clip, line_no};
use crate::model::{Fact, Facts, SymKind};
use crate::settings::GraphSettings;

fn links(line: &str, facts: &mut Facts, settings: &GraphSettings) {
    let mut cursor = 0usize;
    while let Some(pos) = line.get(cursor..).and_then(|t| t.find("](")) {
        let start = cursor.saturating_add(pos).saturating_add(2);
        let Some(rest) = line.get(start..) else { break };
        let end = rest.find(')').unwrap_or(rest.len());
        let target = rest
            .get(..end)
            .unwrap_or("")
            .split('#')
            .next()
            .unwrap_or("")
            .trim();
        if !target.is_empty()
            && !target.contains(':')
            && facts.imports.len() < settings.max_imports_per_file
        {
            let value = format!("md:{target}");
            if !facts.imports.contains(&value) {
                facts.imports.push(value);
            }
        }
        cursor = start;
    }
}

fn mentions(line: &str, facts: &mut Facts, settings: &GraphSettings) {
    for (index, token) in line.split('`').enumerate() {
        if index % 2 == 1
            && token.contains('/')
            && token.len() <= settings.max_path_chars
            && !token.contains(char::is_whitespace)
            && facts.mentions.len() < settings.max_imports_per_file
            && !facts.mentions.iter().any(|m| m == token)
        {
            facts.mentions.push(token.to_owned());
        }
    }
}

#[must_use]
pub fn extract(text: &str, settings: &GraphSettings) -> Facts {
    let mut facts = Facts::default();
    let mut fenced = false;
    for (index, raw) in text.lines().enumerate() {
        let line = raw.trim();
        if line.starts_with("```") || line.starts_with("~~~") {
            fenced = !fenced;
            continue;
        }
        if fenced {
            continue;
        }
        if line.starts_with('#') {
            let title = line.trim_start_matches('#').trim();
            if !title.is_empty() && facts.symbols.len() < settings.max_symbols_per_file {
                facts.symbols.push(Fact {
                    name: clip(title, settings.max_name_chars),
                    kind: SymKind::Entity,
                    line: line_no(index),
                });
            }
        }
        links(line, &mut facts, settings);
        mentions(line, &mut facts, settings);
    }
    facts
}
