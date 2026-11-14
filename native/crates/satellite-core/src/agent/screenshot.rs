use std::path::Path;

use serde_json::Value;

use crate::vault::write_atomic;

const MAX_VALUE: usize = 200;
const KEYS: &[&str] = &[
    "NUXIVA_SCREENSHOT",
    "NUXIVA_SCREENSHOT_TARGET",
    "NUXIVA_SCREENSHOT_SUBDIR",
    "NUXIVA_SCREENSHOT_MASK",
    "NUXIVA_SCREENSHOT_RETENTION_DAYS",
    "NUXIVA_SCREENSHOT_BLOCK_LOCKED",
    "NUXIVA_SCREENSHOT_BLOCK_GUESTS",
    "NUXIVA_SCREENSHOT_NOTICE",
    "NUXIVA_UI_LANG",
];

#[must_use]
pub fn render(reply: &Value) -> Option<String> {
    let settings = reply.get("settings")?.as_object()?;
    let mut out = String::new();
    for key in KEYS {
        let Some(value) = settings.get(*key).and_then(Value::as_str) else {
            continue;
        };
        let value = value.trim();
        if value.len() > MAX_VALUE
            || value
                .chars()
                .any(|c| c.is_control() || c == '"' || c == '\'' || c == '\\')
        {
            continue;
        }
        out.push_str(key);
        out.push('=');
        out.push_str(value);
        out.push('\n');
    }
    if out.is_empty() { None } else { Some(out) }
}

#[must_use]
pub fn sync(reply: &Value, path: &Path) -> bool {
    let Some(text) = render(reply) else {
        return false;
    };
    if std::fs::read_to_string(path).is_ok_and(|current| current == text) {
        return false;
    }
    write_atomic(path, text.as_bytes()).is_ok()
}
