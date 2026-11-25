#![allow(clippy::indexing_slicing)]

use serde_json::{Value, json};

use crate::{HoloError, prepare};

fn run(input: &Value) -> Value {
    let out = prepare(&input.to_string());
    assert!(out.is_ok(), "{out:?}");
    serde_json::from_str(&out.unwrap_or_default()).unwrap_or(Value::Null)
}

fn num(v: &Value) -> f64 {
    v.as_f64().unwrap_or(f64::NAN)
}

#[test]
fn model_parts_are_centered_and_scaled_to_unit_radius() {
    let scene = run(&json!({"title": "Martello", "parts": [
        {"name": "manico", "shape": "cylinder", "radius": 1.6, "height": 30, "position": [0, 15, 0], "color": "#8b5a2b"},
        {"name": "testa", "shape": "box", "size": [11, 3.4, 3.4], "position": [1.5, 31.5, 0], "metal": true}
    ]}));
    assert_eq!(scene["euler"], "XYZ");
    let parts = scene["parts"].as_array().cloned().unwrap_or_default();
    assert_eq!(parts.len(), 2);
    for part in &parts {
        for axis in 0..3 {
            let at = num(&part["at"][axis]);
            let half = num(&part["half"][axis]);
            assert!(at - half >= -1.001 && at + half <= 1.001, "{part}");
        }
    }
    assert!(num(&scene["parts"][1]["metal"]) > 0.5);
    assert_eq!(scene["parts"][0]["color"], "#8b5a2b");
}

#[test]
fn nested_parts_get_deeper_layers_and_core_does_not_explode() {
    let scene = run(&json!({"parts": [
        {"name": "membrana", "shape": "sphere", "radius": 10, "position": [0, 0, 0]},
        {"name": "nucleo", "shape": "sphere", "radius": 3, "position": [0, 0, 0], "motion": "pulse"},
        {"name": "mitocondrio", "shape": "capsule", "radius": 1, "height": 3, "position": [5, 0, 0]}
    ]}));
    assert_eq!(scene["layers"], 2);
    assert_eq!(scene["parts"][0]["layer"], 0);
    assert_eq!(scene["parts"][1]["layer"], 1);
    assert_eq!(scene["parts"][2]["layer"], 1);
    assert!(num(&scene["parts"][1]["explode"][0]).abs() < 1e-6);
    assert_eq!(scene["parts"][1]["motion"], "pulse");
    assert_eq!(scene["parts"][0]["motion"], "none");
    assert!(num(&scene["parts"][2]["explode"][0]) > 0.3);
}

#[test]
fn given_layers_win_over_inference() {
    let scene = run(&json!({"parts": [
        {"name": "a", "shape": "box", "size": [2, 2, 2], "position": [0, 0, 0], "layer": 3},
        {"name": "b", "shape": "box", "size": [1, 1, 1], "position": [0, 0, 0], "layer": 99}
    ]}));
    assert_eq!(scene["parts"][0]["layer"], 3);
    assert_eq!(scene["parts"][1]["layer"], 7);
    assert_eq!(scene["layers"], 8);
}

#[test]
fn particle_spec_maps_every_primitive() {
    let shapes = [
        "sphere", "box", "cylinder", "cone", "torus", "helix", "plane", "cloud", "disc", "spiral",
        "ring", "halo", "orbit",
    ];
    let parts: Vec<Value> = shapes
        .iter()
        .map(|s| json!({"shape": s, "size": [0.5, 0.8, 0.5], "at": [0.1, 0.2, 0.0], "rot": [0, 45, 0], "color": "#29e0ff"}))
        .collect();
    let scene = run(&json!({"source": "particles", "parts": parts}));
    assert_eq!(scene["euler"], "ZYX");
    assert_eq!(scene["parts"].as_array().map(Vec::len), Some(shapes.len()));
    assert_eq!(scene["parts"][7]["soft"], true);
    assert_eq!(scene["parts"][10]["shape"], "torus");
}

#[test]
fn hostile_input_is_sanitized() {
    let scene = run(&json!({"title": "<script>x</script>", "parts": [
        {"name": "a\u{0007}<img onerror=1>", "shape": "box", "size": [1e30, -5, "x"], "position": [f64::MAX, 0, 0], "color": "red", "motion": "explode()"},
        {"shape": "unknown"},
        "nope"
    ]}));
    let title = scene["title"].as_str().unwrap_or_default();
    assert!(!title.contains('<'));
    let name = scene["parts"][0]["name"].as_str().unwrap_or_default();
    assert!(!name.contains('<') && !name.contains('\u{0007}'));
    assert_eq!(scene["parts"].as_array().map(Vec::len), Some(1));
    assert!(
        scene["parts"][0]["color"]
            .as_str()
            .unwrap_or_default()
            .starts_with('#')
    );
}

#[test]
fn empty_and_oversized_input_are_rejected() {
    assert_eq!(prepare("{\"parts\": []}"), Err(HoloError::NoParts));
    assert_eq!(prepare("[]"), Err(HoloError::BadJson));
    assert_eq!(
        prepare(&" ".repeat(crate::MAX_INPUT + 1)),
        Err(HoloError::TooLarge)
    );
}

#[test]
fn part_count_is_capped() {
    let parts: Vec<Value> = (0..300)
        .map(|i| json!({"shape": "box", "size": [1, 1, 1], "position": [i, 0, 0]}))
        .collect();
    let scene = run(&json!({"parts": parts}));
    assert_eq!(
        scene["parts"].as_array().map(Vec::len),
        Some(crate::model::MAX_PARTS)
    );
}
