use super::util::clip;
use crate::model::Facts;
use crate::settings::GraphSettings;

fn section_dependency(header: &str) -> Option<&str> {
    for prefix in ["dependencies.", "dev-dependencies.", "build-dependencies."] {
        if let Some(rest) = header.strip_prefix(prefix) {
            return Some(rest.trim().trim_matches('"'));
        }
        if let Some((_, rest)) = header.split_once(&format!(".{prefix}")) {
            return Some(rest.trim().trim_matches('"'));
        }
    }
    None
}

fn is_dependency_table(header: &str) -> bool {
    let base = header.rsplit('.').next().unwrap_or(header);
    matches!(
        base,
        "dependencies" | "dev-dependencies" | "build-dependencies"
    ) && !header.contains(".dependencies.")
}

#[must_use]
pub fn extract(text: &str, settings: &GraphSettings) -> Facts {
    let mut facts = Facts::default();
    let mut header = String::new();
    for raw in text.lines() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        if let Some(inner) = line.strip_prefix('[').and_then(|r| r.strip_suffix(']')) {
            inner.trim().clone_into(&mut header);
            if let Some(dep) = section_dependency(&header) {
                if facts.imports.len() < settings.max_imports_per_file && !dep.is_empty() {
                    facts
                        .imports
                        .push(format!("dep:{}", clip(dep, settings.max_name_chars)));
                }
            }
            continue;
        }
        let Some((key, value)) = line.split_once('=') else {
            continue;
        };
        let key = key.trim().trim_matches('"');
        if header == "package" && key == "name" && facts.package.is_none() {
            let name = value.trim().trim_matches('"');
            if !name.is_empty() {
                facts.package = Some(clip(name, settings.max_name_chars));
            }
        } else if is_dependency_table(&header)
            && facts.imports.len() < settings.max_imports_per_file
        {
            let name = format!("dep:{}", clip(key, settings.max_name_chars));
            if !facts.imports.contains(&name) {
                facts.imports.push(name);
            }
        }
    }
    facts
}
