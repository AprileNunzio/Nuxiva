#![allow(clippy::indexing_slicing)]

use crate::{MAX_PARTS, Plan, Traits, compile, compose, schema};

fn traits(json: &str) -> Traits {
    serde_json::from_str(json).unwrap_or_default()
}

const MEDUSA: &str = r#"{"symmetry":"radial","body":"bell","length":1.2,"width":1.4,"limb":"hang","limbs":12,"limb_length":1.8,"curl":0.4,"theme":"bioluminescent"}"#;
const BIRD: &str = r#"{"symmetry":"bilateral","body":"spindle","length":2.0,"width":0.5,"limb":"wing","limbs":2,"limb_length":2.2,"theme":"fauna"}"#;
const ATOM: &str = r#"{"symmetry":"orbital","width":1.0,"rings":3,"theme":"microscopic"}"#;
const DNA: &str = r#"{"symmetry":"spiral","length":3.0,"width":0.7,"theme":"microscopic"}"#;
const COLUMN: &str = r#"{"symmetry":"axial","body":"column","length":3.0,"width":0.6,"rings":4}"#;

#[test]
fn archetypes_compile_within_limits() {
    for raw in [MEDUSA, BIRD, ATOM, DNA, COLUMN] {
        let parts = compile(&compose(&traits(raw)));
        let parts = parts.unwrap_or_default();
        assert!(!parts.is_empty() && parts.len() <= MAX_PARTS, "{raw}");
        for p in &parts {
            assert!(p.size.iter().all(|v| (0.01..=10.0).contains(v)));
            assert!(p.at.iter().all(|v| v.abs() <= 10.0));
            assert!(p.rot.iter().all(|v| v.abs() <= 360.0));
        }
    }
}

#[test]
fn the_same_traits_always_give_the_same_parts() {
    let a = serde_json::to_string(&compile(&compose(&traits(MEDUSA))).unwrap_or_default());
    let b = serde_json::to_string(&compile(&compose(&traits(MEDUSA))).unwrap_or_default());
    assert_eq!(a.ok(), b.ok());
}

#[test]
fn radial_symmetry_places_limbs_evenly() {
    let parts = compile(&compose(&traits(MEDUSA))).unwrap_or_default();
    let tips = parts.iter().filter(|p| p.at[1] < -0.8).count();
    assert!(tips >= 12);
    let sum: f64 = parts
        .iter()
        .filter(|p| p.at[1] < -1.2)
        .map(|p| p.at[0])
        .sum();
    assert!(sum.abs() < 0.5);
}

#[test]
fn bilateral_symmetry_mirrors_the_wings() {
    let parts = compile(&compose(&traits(BIRD))).unwrap_or_default();
    let left: f64 = parts
        .iter()
        .filter(|p| p.at[0] > 0.3)
        .map(|p| p.at[0])
        .sum();
    let right: f64 = parts
        .iter()
        .filter(|p| p.at[0] < -0.3)
        .map(|p| p.at[0])
        .sum();
    assert!(left > 0.0 && (left + right).abs() < 1e-6);
}

#[test]
fn hostile_plans_are_rejected() {
    let cases = [
        r#"{"nodes":[{"op":"radial","count":9999,"child":{"op":"blob"}}]}"#,
        r#"{"nodes":[{"op":"radial","count":24,"child":{"op":"radial","count":24,"child":{"op":"blob"}}}]}"#,
        r#"{"nodes":[{"op":"lathe","profile":[[1.0,0.0]]}]}"#,
        r#"{"nodes":[{"op":"lathe","profile":[[-1.0,0.0],[1.0,1.0]]}]}"#,
        r#"{"nodes":[{"op":"sweep","dir":[0,0,0]}]}"#,
        r#"{"nodes":[{"op":"sweep","steps":999}]}"#,
        r#"{"nodes":[{"op":"blob","at":[1e9,0,0]}]}"#,
        r#"{"nodes":[]}"#,
    ];
    for raw in cases {
        let plan: Result<Plan, _> = serde_json::from_str(raw);
        let outcome = plan
            .map_err(|_| ())
            .and_then(|p| compile(&p).map_err(|_| ()));
        assert!(outcome.is_err(), "{raw}");
    }
    assert!(serde_json::from_str::<Plan>(r#"{"nodes":[{"op":"blob","x":1}]}"#).is_err());
    assert!(serde_json::from_str::<Plan>(r#"{"nodes":[],"extra":1}"#).is_err());
}

#[test]
fn deep_nesting_is_refused() {
    let mut raw = String::from(r#"{"op":"blob"}"#);
    for _ in 0..10 {
        raw = format!(r#"{{"op":"mirror","axis":"x","child":{raw}}}"#);
    }
    let plan: Result<Plan, _> = serde_json::from_str(&format!(r#"{{"nodes":[{raw}]}}"#));
    assert!(
        plan.map_err(|_| ())
            .and_then(|p| compile(&p).map_err(|_| ()))
            .is_err()
    );
}

#[test]
fn nonsense_traits_are_clamped_not_fatal() {
    let weird = traits(
        r#"{"symmetry":"qualcosa","body":"boh","length":1e9,"width":-5,"limbs":9999,"rings":99,"curl":9}"#,
    );
    assert!(compile(&compose(&weird)).is_ok());
}

#[test]
fn schema_lists_every_field_of_the_traits() {
    let names: Vec<String> = schema()["fields"]
        .as_array()
        .map(|a| {
            a.iter()
                .filter_map(|f| f["name"].as_str().map(str::to_owned))
                .collect()
        })
        .unwrap_or_default();
    let full = serde_json::to_value(Traits::default()).unwrap_or_default();
    let mut keys: Vec<String> = full
        .as_object()
        .map(|o| o.keys().cloned().collect())
        .unwrap_or_default();
    keys.sort();
    let mut names = names;
    names.sort();
    assert_eq!(keys, names);
}
