#![allow(clippy::indexing_slicing)]

use crate::{Plan, compile, inspect};

fn report(json: &str) -> crate::Report {
    let plan: Plan = serde_json::from_str(json).unwrap_or(Plan {
        theme: String::new(),
        nodes: Vec::new(),
    });
    inspect(&compile(&plan).unwrap_or_default(), 1.0)
}

const JOINED: &str = r#"{"nodes":[
 {"op":"blob","shape":"box","at":[0,0,0],"size":[1,0.5,2]},
 {"op":"mirror","axis":"x","child":{"op":"blob","shape":"cylinder","at":[1.1,-0.5,1],"size":[0.4,0.1,0.4],"rot":[0,0,90]}},
 {"op":"blob","shape":"cylinder","at":[0,0.8,1.5],"size":[0.15,0.4,0.15]},
 {"op":"blob","shape":"sphere","at":[0,0.2,-2.2],"size":[0.3,0.3,0.3]},
 {"op":"blob","shape":"box","at":[0,0.4,0.2],"size":[0.5,0.3,0.5]}]}"#;

const APART: &str = r#"{"nodes":[
 {"op":"blob","shape":"box","at":[0,0,0],"size":[1,0.5,2]},
 {"op":"blob","shape":"sphere","at":[6,0,0],"size":[0.3,0.3,0.3]},
 {"op":"blob","shape":"sphere","at":[-6,2,0],"size":[0.3,0.3,0.3]},
 {"op":"blob","shape":"box","at":[0,0.4,0.2],"size":[0.5,0.3,0.5]},
 {"op":"blob","shape":"box","at":[0,0.4,1.2],"size":[0.5,0.3,0.5]}]}"#;

#[test]
fn a_connected_machine_has_one_component() {
    let r = report(JOINED);
    assert_eq!(r.components, 1);
    assert!(r.loose.is_empty() && !r.issues.contains(&"detached_parts".to_owned()));
    assert!(r.asymmetry < 0.05);
}

#[test]
fn floating_parts_are_found_and_named() {
    let r = report(APART);
    assert!(r.components >= 3);
    assert_eq!(r.loose.len(), 2);
    assert!(r.issues.contains(&"detached_parts".to_owned()));
}

#[test]
fn flat_and_sparse_shapes_are_flagged() {
    let r = report(r#"{"nodes":[{"op":"blob","shape":"plane","size":[2,0.01,2]}]}"#);
    assert!(
        r.issues.contains(&"flat".to_owned()) && r.issues.contains(&"too_few_parts".to_owned())
    );
}

#[test]
fn a_lopsided_object_has_a_large_asymmetry() {
    let r = report(
        r#"{"nodes":[{"op":"blob","shape":"sphere","at":[2,0,0],"size":[0.5,0.5,0.5]},{"op":"blob","shape":"sphere","at":[-1,0,0],"size":[0.1,0.1,0.1],"weight":0.1}]}"#,
    );
    assert!(r.asymmetry > 0.2);
}
