use serde::{Deserialize, Serialize};
use serde_json::{Map, Value, json};

pub const MAX_VERSION: usize = 40;
pub const MAX_CODE: usize = 48;
pub const MAX_NODES: usize = 512;
pub const MAX_HISTORY: usize = 20;
const FUTURE_SKEW: f64 = 86_400.0;
const STATES: [&str; 7] = [
    "idle",
    "checking",
    "downloading",
    "installing",
    "awaiting_user",
    "failed",
    "rolled_back",
];
const CHANNELS: [&str; 5] = ["debian", "android", "windows", "esp32", "other"];

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Failure {
    pub code: String,
    pub at: Option<f64>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct NodeUpdate {
    pub state: String,
    pub channel: String,
    pub version: Option<String>,
    pub target: Option<String>,
    pub last_check: Option<f64>,
    pub last_success: Option<f64>,
    pub last_error: Option<Failure>,
}

fn token(value: &Value, limit: usize, extra: &[char]) -> Option<String> {
    let text = value.as_str()?.trim();
    let valid = !text.is_empty()
        && text.chars().count() <= limit
        && text
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || extra.contains(&c));
    valid.then(|| text.to_owned())
}

fn version(value: Option<&Value>) -> Option<String> {
    token(value?, MAX_VERSION, &['.', '-', '_', '+'])
}

fn code(value: Option<&Value>) -> Option<String> {
    token(value?, MAX_CODE, &['.', '-', '_']).map(|c| c.to_ascii_lowercase())
}

fn stamp(value: Option<&Value>, now: f64) -> Option<f64> {
    let number = value?.as_f64()?;
    (number.is_finite() && number > 0.0 && number <= now + FUTURE_SKEW).then_some(number.floor())
}

#[must_use]
pub fn sanitize(raw: &Value, now: f64) -> Option<NodeUpdate> {
    let object = raw.as_object()?;
    let state = object.get("state")?.as_str()?;
    if !STATES.contains(&state) {
        return None;
    }
    let channel = object
        .get("channel")
        .and_then(Value::as_str)
        .filter(|c| CHANNELS.contains(c))
        .unwrap_or("other");
    let last_error = object
        .get("last_error")
        .and_then(Value::as_object)
        .and_then(|error| {
            Some(Failure {
                code: code(error.get("code"))?,
                at: stamp(error.get("at"), now),
            })
        });
    Some(NodeUpdate {
        state: state.to_owned(),
        channel: channel.to_owned(),
        version: version(object.get("version")),
        target: version(object.get("target")),
        last_check: stamp(object.get("last_check"), now),
        last_success: stamp(object.get("last_success"), now),
        last_error,
    })
}

fn node_status(
    online: bool,
    version: Option<&str>,
    server: Option<&str>,
    update: Option<&NodeUpdate>,
) -> &'static str {
    if !online {
        return "offline";
    }
    let state = update.map_or("idle", |u| u.state.as_str());
    match state {
        "failed" | "rolled_back" => "failed",
        "checking" | "downloading" | "installing" => "updating",
        "awaiting_user" => "awaiting_user",
        _ => match (version, server) {
            (Some(current), Some(wanted)) if current != wanted => "outdated",
            (None, _) => "unknown",
            _ => "up_to_date",
        },
    }
}

fn server_status(state: &str, has_error: bool, available: bool) -> &'static str {
    if matches!(state, "checking" | "downloading" | "installing") {
        "updating"
    } else if has_error {
        "failed"
    } else if available {
        "outdated"
    } else {
        "up_to_date"
    }
}

fn text(value: Option<&Value>, limit: usize) -> Option<String> {
    let raw = value?.as_str()?;
    let clean: String = raw
        .chars()
        .filter(|c| !c.is_control())
        .take(limit)
        .collect();
    let trimmed = clean.trim();
    (!trimmed.is_empty()).then(|| trimmed.to_owned())
}

fn number(value: Option<&Value>) -> Option<f64> {
    let n = value?.as_f64()?;
    (n.is_finite() && n > 0.0).then_some(n)
}

#[must_use]
pub fn overview(input: &Value) -> Value {
    let now = number(input.get("now")).unwrap_or(0.0);
    let empty = Map::new();
    let server = input
        .get("server")
        .and_then(Value::as_object)
        .unwrap_or(&empty);
    let server_version = version(server.get("version"));
    let server_state = server
        .get("state")
        .and_then(Value::as_str)
        .filter(|s| STATES.contains(s))
        .unwrap_or("idle");
    let server_error = text(server.get("last_error"), 160);
    let available = server
        .get("available")
        .and_then(Value::as_bool)
        .unwrap_or(false);
    let server_state_status = server_status(server_state, server_error.is_some(), available);
    let server_view = json!({
        "version": server_version,
        "state": server_state,
        "status": server_state_status,
        "available": available,
        "auto_update": server.get("auto_update").and_then(Value::as_bool).unwrap_or(false),
        "last_check": number(server.get("last_check")),
        "last_success": number(server.get("last_success")),
        "last_error": server_error,
        "next_check": number(server.get("next_check")),
    });
    let nodes: Vec<Value> = input
        .get("nodes")
        .and_then(Value::as_array)
        .map(|list| list.iter().take(MAX_NODES).collect::<Vec<_>>())
        .unwrap_or_default()
        .into_iter()
        .filter_map(|node| node_view(node, server_version.as_deref(), now))
        .collect();
    let count = |status: &str| nodes.iter().filter(|n| n["status"] == status).count();
    let counts = json!({
        "total": nodes.len(),
        "up_to_date": count("up_to_date"),
        "outdated": count("outdated"),
        "updating": count("updating"),
        "failed": count("failed"),
        "awaiting_user": count("awaiting_user"),
        "offline": count("offline"),
        "unknown": count("unknown"),
    });
    let awaiting = count("awaiting_user");
    let outdated = count("outdated").saturating_add(awaiting);
    let summary = if server_state_status == "failed" || count("failed") > 0 {
        "attention"
    } else if server_state_status == "updating" || count("updating") > 0 {
        "updating"
    } else if server_state_status == "outdated" || outdated > 0 {
        "outdated"
    } else {
        "up_to_date"
    };
    json!({"summary": summary, "server": server_view, "nodes": nodes, "counts": counts})
}

fn node_view(node: &Value, server: Option<&str>, now: f64) -> Option<Value> {
    let object = node.as_object()?;
    let id = token(object.get("id")?, 48, &['-', '_'])?;
    let online = object
        .get("online")
        .and_then(Value::as_bool)
        .unwrap_or(false);
    let update = object.get("update").and_then(|raw| sanitize(raw, now));
    let reported =
        version(object.get("version")).or_else(|| update.as_ref().and_then(|u| u.version.clone()));
    let status = node_status(online, reported.as_deref(), server, update.as_ref());
    Some(json!({
        "id": id,
        "name": text(object.get("name"), 60).unwrap_or_else(|| id.clone()),
        "type": text(object.get("type"), 32),
        "online": online,
        "version": reported,
        "status": status,
        "update": update,
        "history": history(object.get("update_history")),
    }))
}

fn history(value: Option<&Value>) -> Vec<Value> {
    value
        .and_then(Value::as_array)
        .map(|list| {
            list.iter()
                .filter_map(|entry| {
                    let object = entry.as_object()?;
                    let state = object
                        .get("state")?
                        .as_str()
                        .filter(|s| STATES.contains(s))?;
                    Some(json!({
                        "at": number(object.get("at")),
                        "state": state,
                        "version": version(object.get("version")),
                        "code": code(object.get("code")),
                    }))
                })
                .rev()
                .take(MAX_HISTORY)
                .collect()
        })
        .unwrap_or_default()
}

#[cfg(test)]
#[allow(
    clippy::unwrap_used,
    clippy::indexing_slicing,
    clippy::float_arithmetic
)]
mod tests {
    use super::*;

    const NOW: f64 = 1_800_000_000.0;

    #[test]
    fn rejects_unknown_state() {
        assert!(sanitize(&json!({"state": "exploding"}), NOW).is_none());
        assert!(sanitize(&json!("idle"), NOW).is_none());
    }

    #[test]
    fn drops_malformed_fields() {
        let report = sanitize(
            &json!({"state": "idle", "channel": "weird", "version": "bad version!", "last_check": 9.9e18,
                    "last_error": {"code": "No Good!"}}),
            NOW,
        )
        .unwrap();
        assert_eq!(report.channel, "other");
        assert!(
            report.version.is_none() && report.last_check.is_none() && report.last_error.is_none()
        );
    }

    #[test]
    fn keeps_valid_report() {
        let report = sanitize(
            &json!({"state": "failed", "channel": "debian", "version": "5.8.3", "last_check": NOW - 5.0,
                    "last_error": {"code": "Hash_Mismatch", "at": NOW - 4.0}}),
            NOW,
        )
        .unwrap();
        assert_eq!(report.last_error.unwrap().code, "hash_mismatch");
        assert_eq!(report.version.as_deref(), Some("5.8.3"));
    }

    #[test]
    fn classifies_fleet() {
        let view = overview(&json!({
            "now": NOW,
            "server": {"version": "5.8.4", "state": "idle", "auto_update": true, "last_check": NOW},
            "nodes": [
                {"id": "a", "online": true, "version": "5.8.4"},
                {"id": "b", "online": true, "version": "5.8.3"},
                {"id": "c", "online": false, "version": "5.8.3"},
                {"id": "d", "online": true, "version": "5.8.3", "update": {"state": "rolled_back"}},
                {"id": "e", "online": true, "version": "5.8.3", "update": {"state": "installing"}},
                {"id": "../x", "online": true}
            ]
        }));
        let statuses: Vec<&str> = view["nodes"]
            .as_array()
            .unwrap()
            .iter()
            .map(|n| n["status"].as_str().unwrap())
            .collect();
        assert_eq!(
            statuses,
            ["up_to_date", "outdated", "offline", "failed", "updating"]
        );
        assert_eq!(view["summary"], "attention");
        assert_eq!(view["counts"]["total"], 5);
    }

    #[test]
    fn server_failure_wins() {
        let view = overview(
            &json!({"now": NOW, "server": {"version": "1", "last_error": "fetch"}, "nodes": []}),
        );
        assert_eq!(view["summary"], "attention");
        let clean = overview(&json!({"now": NOW, "server": {"version": "1"}, "nodes": []}));
        assert_eq!(clean["summary"], "up_to_date");
    }
}
