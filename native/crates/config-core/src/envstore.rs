use std::collections::HashSet;

use nuxiva_guard_core::{decode_value, format_line};

use crate::keys::valid_key;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ConfigError {
    Key(String),
    Value(String),
}

impl ConfigError {
    #[must_use]
    pub fn key(&self) -> &str {
        match self {
            Self::Key(k) | Self::Value(k) => k,
        }
    }
}

impl std::fmt::Display for ConfigError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Key(_) => f.write_str("config.key.invalid"),
            Self::Value(_) => f.write_str("config.value.invalid"),
        }
    }
}

impl std::error::Error for ConfigError {}

fn lines(text: &str) -> Vec<&str> {
    nuxiva_guard_core::split_lines(text)
}

fn split_entry(stripped: &str) -> Option<(&str, &str)> {
    let (key, value) = stripped.split_once('=')?;
    let key = nuxiva_guard_core::py_strip(key).trim_matches(['"', '\'']);
    Some((key, value))
}

#[must_use]
pub fn parse_env(text: &str) -> Vec<(String, String)> {
    let mut seen = HashSet::new();
    let mut out = Vec::new();
    for raw in lines(text) {
        let line = nuxiva_guard_core::py_strip(raw);
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let Some((key, value)) = split_entry(line) else {
            continue;
        };
        if valid_key(key) && seen.insert(key.to_owned()) {
            out.push((key.to_owned(), decode_value(value)));
        }
    }
    out
}

fn render(key: &str, value: &str) -> Result<String, ConfigError> {
    format_line(key, &decode_value(value)).map_err(|_| ConfigError::Value(key.to_owned()))
}

pub fn rewrite_env(text: &str, updates: &[(String, String)]) -> Result<String, ConfigError> {
    for (key, value) in updates {
        if !valid_key(key) {
            return Err(ConfigError::Key(key.clone()));
        }
        if value.contains(['\n', '\r', '\0']) {
            return Err(ConfigError::Value(key.clone()));
        }
    }
    let mut pending: Vec<(String, String)> = Vec::new();
    for (key, value) in updates {
        match pending.iter_mut().find(|(k, _)| k == key) {
            Some(slot) => slot.1.clone_from(value),
            None => pending.push((key.clone(), value.clone())),
        }
    }
    let mut out = Vec::new();
    let mut seen = HashSet::new();
    for raw in lines(text) {
        let stripped = nuxiva_guard_core::py_strip(raw);
        if stripped.is_empty() {
            continue;
        }
        if stripped.starts_with('#') {
            out.push(stripped.to_owned());
            continue;
        }
        let Some((key, value)) = split_entry(stripped) else {
            continue;
        };
        if !valid_key(key) || !seen.insert(key.to_owned()) {
            continue;
        }
        if let Some(index) = pending.iter().position(|(k, _)| k == key) {
            let (_, replacement) = pending.remove(index);
            if !replacement.is_empty() {
                out.push(render(key, &replacement)?);
            }
        } else {
            out.push(render(key, value)?);
        }
    }
    for (key, value) in &pending {
        if !value.is_empty() {
            out.push(render(key, value)?);
        }
    }
    let mut joined = out.join("\n");
    joined.push('\n');
    Ok(joined)
}
