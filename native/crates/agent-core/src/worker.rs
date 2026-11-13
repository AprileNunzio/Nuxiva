use crate::manifest::Issue;
use crate::text::has_control;
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};

pub const MAX_KIND: usize = 32;
pub const MAX_SCOPE: usize = 64;
pub const MAX_SCOPE_ITEM: usize = 128;
pub const MAX_CONCURRENCY: u64 = 256;
pub const MAX_TOKENS: u64 = 10_000_000;
pub const MAX_TOOL_CALLS: u64 = 10_000;
pub const MAX_TIME_MS: u64 = 86_400_000;

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct WorkerBlock {
    pub kind: String,
    pub concurrency_max: u64,
    pub tokens_max: u64,
    pub tool_calls_max: u64,
    pub time_ms: u64,
    pub tools_scope: Vec<String>,
    pub needs_graph: bool,
}

fn bounded(value: Option<&Value>, max: u64, field: &str, issues: &mut Vec<Issue>) -> u64 {
    let Some(raw) = value.filter(|v| !v.is_null()) else {
        return 0;
    };
    if let Some(n) = raw.as_i64() {
        return match u64::try_from(n) {
            Ok(n) if n <= max => n,
            _ => {
                issues.push(Issue::error(field, "out_of_range"));
                0
            }
        };
    }
    if raw.as_u64().is_some() {
        issues.push(Issue::error(field, "out_of_range"));
    } else {
        issues.push(Issue::error(field, "type_number"));
    }
    0
}

fn kind(map: &Map<String, Value>, issues: &mut Vec<Issue>) -> String {
    match map.get("kind") {
        None | Some(Value::Null) => String::new(),
        Some(Value::String(s)) => {
            let trimmed = s.trim();
            let ok = !trimmed.is_empty()
                && trimmed.chars().count() <= MAX_KIND
                && trimmed
                    .chars()
                    .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '_');
            if ok {
                trimmed.to_owned()
            } else {
                issues.push(Issue::error("worker.kind", "invalid"));
                String::new()
            }
        }
        Some(_) => {
            issues.push(Issue::error("worker.kind", "type_string"));
            String::new()
        }
    }
}

fn scope(value: Option<&Value>, issues: &mut Vec<Issue>) -> Vec<String> {
    let Some(raw) = value.filter(|v| !v.is_null()) else {
        return Vec::new();
    };
    let Some(items) = raw.as_array() else {
        issues.push(Issue::error("worker.tools_scope", "type_list"));
        return Vec::new();
    };
    if items.len() > MAX_SCOPE {
        issues.push(Issue::error("worker.tools_scope", "too_many"));
        return Vec::new();
    }
    let mut out: Vec<String> = Vec::with_capacity(items.len());
    for item in items {
        let Some(text) = item.as_str().map(str::trim) else {
            issues.push(Issue::error("worker.tools_scope", "type_item"));
            continue;
        };
        if text.is_empty() {
            continue;
        }
        if has_control(text) || text.chars().count() > MAX_SCOPE_ITEM {
            issues.push(Issue::error("worker.tools_scope", "invalid"));
        } else if !out.iter().any(|known| known == text) {
            out.push(text.to_owned());
        }
    }
    out
}

fn graph_flag(map: &Map<String, Value>, issues: &mut Vec<Issue>) -> bool {
    match map.get("needs_graph") {
        None | Some(Value::Null) => false,
        Some(Value::Bool(b)) => *b,
        Some(_) => {
            issues.push(Issue::error("worker.needs_graph", "type_bool"));
            false
        }
    }
}

pub fn parse(obj: &Map<String, Value>, issues: &mut Vec<Issue>) -> Option<WorkerBlock> {
    let raw = obj.get("worker").filter(|v| !v.is_null())?;
    let Some(map) = raw.as_object() else {
        issues.push(Issue::error("worker", "type_object"));
        return None;
    };
    Some(WorkerBlock {
        kind: kind(map, issues),
        concurrency_max: bounded(
            map.get("concurrency_max"),
            MAX_CONCURRENCY,
            "worker.concurrency_max",
            issues,
        ),
        tokens_max: bounded(
            map.get("tokens_max"),
            MAX_TOKENS,
            "worker.tokens_max",
            issues,
        ),
        tool_calls_max: bounded(
            map.get("tool_calls_max"),
            MAX_TOOL_CALLS,
            "worker.tool_calls_max",
            issues,
        ),
        time_ms: bounded(map.get("time_ms"), MAX_TIME_MS, "worker.time_ms", issues),
        tools_scope: scope(map.get("tools_scope"), issues),
        needs_graph: graph_flag(map, issues),
    })
}
