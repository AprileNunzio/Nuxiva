use crate::manifest::Issue;
use crate::text::has_control;
use serde_json::Value;
use std::collections::BTreeSet;
use std::fs;
use std::path::Path;

pub const CATEGORIES: &[&str] = &[
    "safety",
    "conversation",
    "personal",
    "home",
    "work",
    "media",
    "info",
    "system",
    "ambient",
];
pub const MODES: &[&str] = &["collapse", "open"];
pub const LANGUAGES: &[&str] = &["it", "en", "fr", "es"];
pub const MEDIA: &[&str] = &["audio", "video"];
pub const MAX_ID: usize = 41;
pub const MAX_ICON: usize = 24;
pub const MAX_TITLE: usize = 60;
pub const MAX_SAY: usize = 90;
pub const MAX_FILE: u64 = 256 * 1024;
pub const TITLE_KEY: &str = "simple_title";
pub const SAY_PREFIX: &str = "say_";

fn valid_id(id: &str) -> bool {
    let bytes = id.as_bytes();
    let Some(first) = bytes.first() else {
        return false;
    };
    bytes.len() >= 2
        && bytes.len() <= MAX_ID
        && (first.is_ascii_lowercase() || first.is_ascii_digit())
        && bytes
            .iter()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || *b == b'_' || *b == b'-')
}

fn valid_icon(icon: &str) -> bool {
    !icon.is_empty()
        && icon.len() <= MAX_ICON
        && icon
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_')
}

fn text<'a>(manifest: &'a Value, key: &str) -> Option<&'a str> {
    manifest.get(key).and_then(Value::as_str)
}

#[must_use]
pub fn check_manifest(manifest: &Value) -> Vec<Issue> {
    let mut issues = Vec::new();
    if !text(manifest, "id").is_some_and(valid_id) {
        issues.push(Issue::error("id", "invalid"));
    }
    if !text(manifest, "category").is_some_and(|c| CATEGORIES.contains(&c)) {
        issues.push(Issue::error("category", "invalid"));
    }
    if manifest.get("chrome") != Some(&Value::Bool(false)) {
        issues.push(Issue::error("chrome", "must_be_false"));
    }
    for key in ["media", "exclusive"] {
        if let Some(value) = manifest.get(key) {
            if !value.as_str().is_some_and(|m| MEDIA.contains(&m)) {
                issues.push(Issue::error(key, "invalid"));
            }
        }
    }
    match manifest.get("simple") {
        Some(simple) if simple.is_object() => {
            if !text(simple, "mode").is_some_and(|m| MODES.contains(&m)) {
                issues.push(Issue::error("simple.mode", "invalid"));
            }
            if !text(simple, "icon").is_some_and(valid_icon) {
                issues.push(Issue::error("simple.icon", "invalid"));
            }
        }
        _ => issues.push(Issue::error("simple", "missing")),
    }
    issues
}

fn real_file_within(path: &Path, limit: u64) -> bool {
    fs::symlink_metadata(path).is_ok_and(|m| m.file_type().is_file() && m.len() <= limit)
}

fn dictionary(path: &Path) -> Option<serde_json::Map<String, Value>> {
    if !real_file_within(path, MAX_FILE) {
        return None;
    }
    let raw = fs::read_to_string(path).ok()?;
    let doc: Value = serde_json::from_str(&raw).ok()?;
    doc.get("dictionary")?.as_object().cloned()
}

fn check_language(dir: &Path, issues: &mut Vec<Issue>) -> Vec<BTreeSet<String>> {
    let mut sets = Vec::new();
    for lang in LANGUAGES {
        let field = format!("language/{lang}.json");
        let Some(words) = dictionary(&dir.join(&field)) else {
            issues.push(Issue::error(&field, "unreadable"));
            continue;
        };
        let title = words.get(TITLE_KEY).and_then(Value::as_str).map(str::trim);
        if !title
            .is_some_and(|t| !t.is_empty() && t.chars().count() <= MAX_TITLE && !has_control(t))
        {
            issues.push(Issue::error(&field, "simple_title.invalid"));
        }
        let mut keys = BTreeSet::new();
        for (key, value) in &words {
            if !key.starts_with(SAY_PREFIX) {
                continue;
            }
            keys.insert(key.clone());
            let ok = value.as_str().is_some_and(|v| {
                !v.trim().is_empty() && v.chars().count() <= MAX_SAY && !has_control(v)
            });
            if !ok {
                issues.push(Issue::error(&field, "say.invalid"));
            }
        }
        sets.push(keys);
    }
    sets
}

#[must_use]
pub fn inspect(dir: &Path) -> Vec<Issue> {
    let manifest_path = dir.join("widget.json");
    let manifest = if real_file_within(&manifest_path, MAX_FILE) {
        fs::read_to_string(&manifest_path)
            .ok()
            .and_then(|raw| serde_json::from_str::<Value>(&raw).ok())
    } else {
        None
    };
    let Some(manifest) = manifest else {
        return vec![Issue::error("widget.json", "unreadable")];
    };
    let mut issues = check_manifest(&manifest);
    let sets = check_language(dir, &mut issues);
    if sets.windows(2).any(|pair| pair.first() != pair.get(1)) {
        issues.push(Issue::error("language", "say_mismatch"));
    }
    let collapse = manifest
        .get("simple")
        .and_then(|s| text(s, "mode"))
        .is_some_and(|m| m == "collapse");
    if collapse {
        let script = dir.join("widget.js");
        let has_headline = real_file_within(&script, MAX_FILE)
            && fs::read_to_string(&script).is_ok_and(|s| s.contains("headline"));
        if !has_headline {
            issues.push(Issue::error("widget.js", "headline.missing"));
        }
        if sets.iter().all(BTreeSet::is_empty) && sets.len() == LANGUAGES.len() {
            issues.push(Issue::error("language", "say_missing"));
        }
    }
    issues.sort_by(|a, b| (&a.field, &a.code).cmp(&(&b.field, &b.code)));
    issues
}
