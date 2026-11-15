use serde_json::{Map, Number, Value};

pub const METRIC_LIMITS: [(&str, f64, f64); 12] = [
    ("cpu", 0.0, 100.0),
    ("ram", 0.0, 100.0),
    ("disk", 0.0, 100.0),
    ("gpu", 0.0, 100.0),
    ("battery", 0.0, 100.0),
    ("temp", -60.0, 200.0),
    ("uptime", 0.0, 1e10),
    ("power_w", 0.0, 5000.0),
    ("rtt_ms", 0.0, 60000.0),
    ("rx_kbps", 0.0, 1e9),
    ("tx_kbps", 0.0, 1e9),
    ("charging", 0.0, 1.0),
];

pub const PROXIMITY_LIMITS: [(&str, f64, f64); 5] = [
    ("audio_level", 0.0, 1.0),
    ("speech", 0.0, 1.0),
    ("face", 0.0, 1.0),
    ("motion", 0.0, 1.0),
    ("screen_on", 0.0, 1.0),
];

fn number_of(value: &Value) -> Option<f64> {
    match value {
        Value::Bool(flag) => Some(if *flag { 1.0 } else { 0.0 }),
        Value::Number(number) => number.as_f64().filter(|v| v.is_finite()),
        _ => None,
    }
}

#[must_use]
pub fn bounded_round(value: f64, low: f64, high: f64) -> f64 {
    let clamped = value.clamp(low, high);
    let scale = if high <= 1.0 { 1000.0 } else { 10.0 };
    (clamped * scale).round_ties_even() / scale
}

fn bounded(raw: &Value, limits: &[(&str, f64, f64)]) -> Map<String, Value> {
    let mut out = Map::new();
    let Some(object) = raw.as_object() else {
        return out;
    };
    for (key, low, high) in limits {
        let Some(value) = object.get(*key).and_then(number_of) else {
            continue;
        };
        if let Some(number) = Number::from_f64(bounded_round(value, *low, *high)) {
            out.insert((*key).to_owned(), Value::Number(number));
        }
    }
    out
}

#[must_use]
pub fn clean_metrics(raw: &Value) -> Map<String, Value> {
    bounded(raw, &METRIC_LIMITS)
}

#[must_use]
pub fn clean_proximity(raw: &Value, now: f64) -> Map<String, Value> {
    let mut out = bounded(raw, &PROXIMITY_LIMITS);
    if !out.is_empty()
        && now.is_finite()
        && let Some(at) = Number::from_f64((now * 10.0).round_ties_even() / 10.0)
    {
        out.insert("at".to_owned(), Value::Number(at));
    }
    out
}
