#![allow(clippy::indexing_slicing)]

use crate::{Anatomy, MAX_PARTS, compile, compose_anatomy, preset};

const CONCEPTS: &[&str] = &[
    "un cane", "gatto", "cavallo", "elefante", "giraffa", "coniglio", "orso", "drago", "uomo",
    "robot", "scimmia", "aquila", "anatra", "squalo", "pesce", "serpente", "ragno", "farfalla",
    "ape", "cervo", "topo",
];

fn parts(a: &Anatomy) -> Vec<crate::Part> {
    compile(&compose_anatomy(a)).unwrap_or_default()
}

#[test]
fn every_known_concept_builds_a_rich_shape_within_limits() {
    for name in CONCEPTS {
        let found = preset(name).unwrap_or_default();
        let anatomy = found.unwrap_or_default();
        assert!(preset(name).unwrap_or_default().is_some(), "{name}");
        let built = parts(&anatomy);
        assert!(
            built.len() >= 12 && built.len() <= MAX_PARTS,
            "{name}: {}",
            built.len()
        );
        for p in &built {
            assert!(p.size.iter().all(|v| (0.01..=10.0).contains(v)), "{name}");
            assert!(p.at.iter().all(|v| v.abs() <= 10.0), "{name}");
        }
    }
}

#[test]
fn polite_phrases_and_plurals_find_the_same_body_plan() {
    for (phrase, plan) in [
        ("Mi mostri un cane", "quadruped"),
        ("i miei gatti", "quadruped"),
        ("una farfalla blu", "insect"),
        ("a shark", "fish"),
        ("an eagle", "bird"),
    ] {
        let a = preset(phrase).unwrap_or_default().unwrap_or_default();
        assert_eq!(a.plan, plan, "{phrase}");
    }
    assert!(preset("una sedia").unwrap_or_default().is_none());
    assert!(preset("catena").unwrap_or_default().is_none());
}

#[test]
fn the_body_is_mirrored_left_and_right() {
    let dog = Anatomy {
        tail_curl: 0.0,
        ..preset("cane").unwrap_or_default().unwrap_or_default()
    };
    let built = parts(&dog);
    let right: f64 = built
        .iter()
        .filter(|p| p.at[0] > 0.05)
        .map(|p| p.at[0])
        .sum();
    let left: f64 = built
        .iter()
        .filter(|p| p.at[0] < -0.05)
        .map(|p| p.at[0])
        .sum();
    assert!((right + left).abs() < 0.05 * right.abs().max(1.0));
}

#[test]
fn proportions_change_the_silhouette() {
    let base = preset("cavallo").unwrap_or_default().unwrap_or_default();
    let tall = Anatomy {
        legs: 2.2,
        ..base.clone()
    };
    let low = Anatomy { legs: 0.4, ..base };
    let height = |a: &Anatomy| {
        let b = parts(a);
        let top = b
            .iter()
            .map(|p| p.at[1] + p.size[1])
            .fold(f64::MIN, f64::max);
        let bottom = b
            .iter()
            .map(|p| p.at[1] - p.size[1])
            .fold(f64::MAX, f64::min);
        top - bottom
    };
    assert!(height(&tall) > height(&low));
}

#[test]
fn nonsense_values_are_clamped_and_unknown_fields_refused() {
    let wild = Anatomy {
        size: f64::NAN,
        legs: 1e9,
        neck: -4.0,
        pairs: 9999,
        wings: f64::INFINITY,
        ..Anatomy::default()
    };
    assert!(!parts(&wild).is_empty());
    assert!(serde_json::from_str::<Anatomy>(r#"{"plan":"bird","evil":1}"#).is_err());
    let odd = Anatomy {
        plan: "x".to_owned(),
        ..Anatomy::default()
    };
    assert!(!parts(&odd).is_empty());
}

#[test]
fn the_cat_names_its_anatomy() {
    let cat = preset("gatto").unwrap_or_default().unwrap_or_default();
    let (_, labels) = crate::compile_full(&compose_anatomy(&cat)).unwrap_or_default();
    let names: Vec<&str> = labels.iter().map(|l| l.name.as_str()).collect();
    for want in ["head", "ears", "tail", "front_legs", "hind_legs", "body"] {
        assert!(names.contains(&want), "{want}");
    }
    let unique: std::collections::BTreeSet<&&str> = names.iter().collect();
    assert_eq!(unique.len(), names.len());
}
