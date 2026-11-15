use serde_json::{Map, Number, Value, json};

const WEIGHTS: [(&str, f64); 4] = [
    ("speech", 0.4),
    ("audio_level", 0.25),
    ("face", 0.25),
    ("motion", 0.1),
];
const TTL: f64 = 45.0;
const FLOOR: f64 = 0.12;
const HALF_LIFE: f64 = 12.0;
const MARGIN: f64 = 0.08;
const CLOCK_SKEW: f64 = 5.0;
const MAX_NODES: usize = 512;

fn field(signals: &Map<String, Value>, key: &str) -> f64 {
    signals.get(key).and_then(Value::as_f64).unwrap_or(0.0)
}

#[must_use]
pub fn score(signals: &Map<String, Value>, now: f64) -> f64 {
    let Some(at) = signals.get("at").and_then(Value::as_f64) else {
        return 0.0;
    };
    let age = now - at;
    if !(-CLOCK_SKEW..=TTL).contains(&age) {
        return 0.0;
    }
    let age = age.max(0.0);
    let mut raw: f64 = WEIGHTS
        .iter()
        .map(|(key, weight)| field(signals, key) * weight)
        .sum();
    if field(signals, "screen_on") >= 0.5 {
        raw = (raw + 0.05).min(1.0);
    }
    raw * 0.5_f64.powf(age / HALF_LIFE)
}

fn truthy(value: Option<&Value>) -> bool {
    match value {
        Some(Value::Bool(flag)) => *flag,
        Some(Value::Number(number)) => number.as_f64().is_some_and(|v| v != 0.0),
        _ => false,
    }
}

fn round3(value: f64) -> Value {
    Number::from_f64((value * 1000.0).round_ties_even() / 1000.0).map_or(Value::Null, Value::Number)
}

#[must_use]
pub fn nearest(nodes: &Value, now: f64) -> Value {
    let empty = Map::new();
    let mut ranked: Vec<(f64, String)> = nodes
        .as_array()
        .map(Vec::as_slice)
        .unwrap_or_default()
        .iter()
        .take(MAX_NODES)
        .filter_map(|node| {
            let id = node.get("id")?.as_str()?.to_owned();
            truthy(node.get("online")).then(|| {
                let signals = node
                    .get("proximity")
                    .and_then(Value::as_object)
                    .unwrap_or(&empty);
                (score(signals, now), id)
            })
        })
        .collect();
    ranked.sort_by(|a, b| b.0.total_cmp(&a.0).then_with(|| b.1.cmp(&a.1)));
    let mut scores = Map::new();
    for (value, id) in &ranked {
        scores.insert(id.clone(), round3(*value));
    }
    let best = ranked.first().map_or(0.0, |entry| entry.0);
    let second = ranked.get(1).map_or(0.0, |entry| entry.0);
    let Some((_, winner)) = ranked.first() else {
        return json!({"node_id": null, "confidence": 0.0, "scores": scores});
    };
    if best < FLOOR {
        return json!({"node_id": null, "confidence": 0.0, "scores": scores});
    }
    if best - second < MARGIN {
        return json!({"node_id": null, "confidence": round3(best), "scores": scores, "ambiguous": true});
    }
    json!({
        "node_id": winner,
        "confidence": round3((best - second + best / 2.0).min(1.0)),
        "scores": scores,
    })
}
