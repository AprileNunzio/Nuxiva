use crate::proximity::nearest;
use crate::telemetry::{clean_metrics, clean_proximity};
use serde_json::{Value, json};

fn node(id: &str, now: f64, signals: &Value) -> Value {
    json!({"id": id, "online": true, "proximity": clean_proximity(signals, now)})
}

#[test]
fn metrics_clamp_round_and_drop() {
    let out = clean_metrics(
        &json!({"cpu": 140, "ram": 41.234, "power_w": 6.2, "gpu": -5, "charging": true, "evil": 1, "temp": "x"}),
    );
    assert_eq!(out.get("cpu"), Some(&json!(100.0)));
    assert_eq!(out.get("ram"), Some(&json!(41.2)));
    assert_eq!(out.get("gpu"), Some(&json!(0.0)));
    assert_eq!(out.get("charging"), Some(&json!(1.0)));
    assert!(out.get("evil").is_none());
    assert!(out.get("temp").is_none());
    assert!(clean_metrics(&json!("x")).is_empty());
}

#[test]
fn proximity_has_timestamp_only_with_signals() {
    assert!(clean_proximity(&json!({}), 10.0).is_empty());
    let out = clean_proximity(&json!({"speech": 0.9}), 10.04);
    assert_eq!(out.get("at"), Some(&json!(10.0)));
}

#[test]
fn clear_winner_ambiguous_stale_and_none() {
    let winner = nearest(
        &json!([
            node(
                "phone",
                100.0,
                &json!({"speech": 0.9, "audio_level": 0.7, "face": 0.5})
            ),
            node("server", 100.0, &json!({"speech": 0.2, "audio_level": 0.2}))
        ]),
        101.0,
    );
    assert_eq!(winner["node_id"], json!("phone"));
    let tie = nearest(
        &json!([
            node("a", 100.0, &json!({"speech": 0.8, "audio_level": 0.6})),
            node("b", 100.0, &json!({"speech": 0.79, "audio_level": 0.6}))
        ]),
        100.0,
    );
    assert_eq!(tie["node_id"], Value::Null);
    assert_eq!(tie["ambiguous"], json!(true));
    let stale = nearest(
        &json!([node(
            "old",
            0.0,
            &json!({"speech": 1.0, "audio_level": 1.0})
        )]),
        100.0,
    );
    assert_eq!(stale["node_id"], Value::Null);
    assert_eq!(nearest(&json!([]), 0.0)["node_id"], Value::Null);
    assert_eq!(nearest(&json!("bad"), 0.0)["node_id"], Value::Null);
}

#[test]
fn offline_nodes_are_ignored() {
    let mut off = node("off", 100.0, &json!({"speech": 1.0}));
    off["online"] = json!(false);
    assert_eq!(nearest(&json!([off]), 100.0)["node_id"], Value::Null);
}

#[test]
fn small_clock_skew_is_tolerated() {
    let out = nearest(
        &json!([node(
            "a",
            100.04,
            &json!({"speech": 0.9, "audio_level": 0.8})
        )]),
        100.0,
    );
    assert_eq!(out["node_id"], json!("a"));
}
