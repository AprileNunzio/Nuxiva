#![allow(clippy::indexing_slicing, clippy::arithmetic_side_effects)]

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

#[test]
fn dna_follows_b_form_and_pairs_bases() {
    let out = crate::dna::generate("atgcxx");
    assert!(out.is_ok());
    let scene: Value = serde_json::from_str(&out.unwrap_or_default()).unwrap_or(Value::Null);
    let parts = scene["parts"].as_array().cloned().unwrap_or_default();
    assert_eq!(parts.len(), 4 * 7 + 3 * 2);
    let names: Vec<&str> = parts.iter().filter_map(|p| p["name"].as_str()).collect();
    assert_eq!(names.iter().filter(|n| **n == "dna_adenine").count(), 2);
    assert_eq!(names.iter().filter(|n| **n == "dna_thymine").count(), 2);
    assert_eq!(names.iter().filter(|n| **n == "dna_backbone").count(), 6);
    assert_eq!(scene["layers"], 2);
}

#[test]
fn dna_sequence_is_sanitized_and_bounded() {
    assert_eq!(crate::dna::sequence("<script>"), "ATGCGTACCGATTGCAGCTA");
    assert_eq!(
        crate::dna::sequence(&"GC".repeat(100)).len(),
        crate::dna::MAX_PAIRS
    );
    assert_eq!(crate::dna::sequence("a t g c"), "ATGC");
}

#[test]
fn rod_rotation_points_cylinder_axis_along_segment() {
    let parts = crate::dna::parts("ATGC");
    let rod = parts
        .iter()
        .find(|p| p["name"] == "dna_backbone")
        .cloned()
        .unwrap_or(Value::Null);
    let rx = num(&rod["rotation"][0]).to_radians();
    let rz = num(&rod["rotation"][2]).to_radians();
    let axis = [-rz.sin(), rz.cos() * rx.cos(), rz.cos() * rx.sin()];
    let first = parts
        .iter()
        .filter(|p| p["name"] == "dna_phosphate")
        .map(|p| {
            [
                num(&p["position"][0]),
                num(&p["position"][1]),
                num(&p["position"][2]),
            ]
        })
        .collect::<Vec<_>>();
    let d = [
        first[2][0] - first[0][0],
        first[2][1] - first[0][1],
        first[2][2] - first[0][2],
    ];
    let len = (d[0] * d[0] + d[1] * d[1] + d[2] * d[2]).sqrt();
    let dot = (axis[0] * d[0] + axis[1] * d[1] + axis[2] * d[2]) / len;
    assert!((dot - 1.0).abs() < 1e-3, "{dot}");
}

fn glb(json: &Value) -> Vec<u8> {
    let mut text = json.to_string().into_bytes();
    while text.len() % 4 != 0 {
        text.push(b' ');
    }
    let total = 12 + 8 + text.len();
    let mut out = Vec::new();
    out.extend_from_slice(b"glTF");
    out.extend_from_slice(&2_u32.to_le_bytes());
    out.extend_from_slice(&u32::try_from(total).unwrap_or(0).to_le_bytes());
    out.extend_from_slice(&u32::try_from(text.len()).unwrap_or(0).to_le_bytes());
    out.extend_from_slice(&0x4E4F_534A_u32.to_le_bytes());
    out.extend_from_slice(&text);
    out
}

fn model(animated: bool, ground: bool) -> Value {
    let mut accessors = vec![
        json!({"count": 60000, "min": [-1, -1, -1], "max": [1, 1, 1]}),
        json!({"count": 90000}),
    ];
    let mut meshes =
        vec![json!({"primitives": [{"attributes": {"POSITION": 0}, "indices": 1, "material": 0}]})];
    for _ in 0..3 {
        accessors.push(json!({"count": 300, "min": [0, 0, 0], "max": [1, 1, 1]}));
        let index = accessors.len() - 1;
        meshes.push(json!({"primitives": [{"attributes": {"POSITION": index}}]}));
    }
    if ground {
        accessors.push(json!({"count": 4, "min": [-100, 0, -100], "max": [100, 0, 100]}));
        let index = accessors.len() - 1;
        meshes.push(json!({"primitives": [{"attributes": {"POSITION": index}}]}));
    }
    json!({"asset": {"version": "2.0"}, "accessors": accessors, "meshes": meshes,
           "materials": [{"pbrMetallicRoughness": {"baseColorTexture": {"index": 0}}, "normalTexture": {"index": 1}}],
           "textures": [{}, {}], "animations": if animated { json!([{}]) } else { json!([]) }})
}

#[test]
fn professional_animated_model_scores_high() {
    let report = crate::glb::inspect(&glb(&model(true, false)));
    assert!(report.is_ok());
    let report = report.unwrap_or_default();
    assert_eq!(report.triangles, 30_000 + 300);
    assert_eq!(report.animations, 1);
    assert!(!report.background_suspect);
    assert_eq!(report.score, 100);
}

#[test]
fn ground_plane_and_static_lower_the_score() {
    let report = crate::glb::inspect(&glb(&model(false, true))).unwrap_or_default();
    assert!(report.background_suspect);
    assert!(report.reasons.contains(&"background"));
    assert!(report.reasons.contains(&"static"));
    assert!(report.score <= 60);
}

#[test]
fn external_uris_and_unknown_extensions_are_unusable() {
    let mut value = model(true, false);
    value["buffers"] = json!([{"uri": "file:///etc/passwd", "byteLength": 10}]);
    value["extensionsRequired"] = json!(["KHR_draco_mesh_compression"]);
    let report = crate::glb::inspect(&glb(&value)).unwrap_or_default();
    assert_eq!(report.score, 0);
    assert_eq!(report.external_uris, 1);
    assert_eq!(
        report.unsupported,
        vec!["KHR_draco_mesh_compression".to_owned()]
    );
}

#[test]
fn malformed_containers_are_rejected() {
    assert_eq!(crate::glb::inspect(b"nope"), Err(HoloError::BadModel));
    let mut bytes = glb(&model(true, false));
    bytes.truncate(bytes.len() - 4);
    assert_eq!(crate::glb::inspect(&bytes), Err(HoloError::BadModel));
    let mut lying = glb(&model(true, false));
    lying[12..16].copy_from_slice(&u32::MAX.to_le_bytes());
    assert_eq!(crate::glb::inspect(&lying), Err(HoloError::BadModel));
}
