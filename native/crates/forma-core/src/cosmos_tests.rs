#![allow(clippy::indexing_slicing)]

use crate::{Cosmos, MAX_PARTS, compile_full, compose_cosmos, cosmos_preset};

const CONCEPTS: &[&str] = &[
    "una galassia",
    "la via lattea",
    "un buco nero",
    "una nebulosa",
    "il sistema solare",
    "una stella",
    "il sole",
    "saturno",
    "giove",
    "nettuno",
    "marte",
    "la terra",
    "un pianeta",
    "a galaxy",
    "black hole",
];

#[test]
fn every_celestial_concept_builds_a_named_shape_within_limits() {
    for name in CONCEPTS {
        let cosmos = cosmos_preset(name).unwrap_or_default();
        assert!(cosmos.is_some(), "{name}");
        let (parts, labels) =
            compile_full(&compose_cosmos(&cosmos.unwrap_or_default())).unwrap_or_default();
        assert!(
            parts.len() >= 2 && parts.len() <= MAX_PARTS,
            "{name}: {}",
            parts.len()
        );
        assert!(!labels.is_empty(), "{name}");
        for p in &parts {
            assert!(p.size.iter().all(|v| (0.01..=10.0).contains(v)), "{name}");
            assert!(p.at.iter().all(|v| v.abs() <= 10.0), "{name}");
        }
    }
}

#[test]
fn the_right_kind_is_chosen() {
    for (phrase, kind) in [
        ("una galassia a spirale", "galaxy"),
        ("un buco nero", "blackhole"),
        ("saturno e i suoi anelli", "planet"),
        ("il sistema solare", "system"),
        ("la nebulosa di orione", "nebula"),
        ("una stella", "star"),
    ] {
        assert_eq!(
            cosmos_preset(phrase)
                .unwrap_or_default()
                .unwrap_or_default()
                .kind,
            kind,
            "{phrase}"
        );
    }
    assert!(cosmos_preset("una sedia").unwrap_or_default().is_none());
}

#[test]
fn a_spiral_galaxy_has_one_part_per_arm() {
    let count = |arms: u32| {
        let c = Cosmos {
            kind: "galaxy".to_owned(),
            arms,
            ..Cosmos::default()
        };
        compile_full(&compose_cosmos(&c))
            .unwrap_or_default()
            .0
            .len()
    };
    assert_eq!(count(4).saturating_sub(count(2)), 2);
}

#[test]
fn saturn_has_rings_and_a_jupiter_has_bands() {
    let saturn = cosmos_preset("saturno")
        .unwrap_or_default()
        .unwrap_or_default();
    let (_, labels) = compile_full(&compose_cosmos(&saturn)).unwrap_or_default();
    let names: Vec<&str> = labels.iter().map(|l| l.name.as_str()).collect();
    assert!(names.contains(&"rings") && names.contains(&"bands"));
}

#[test]
fn nonsense_is_clamped() {
    let wild = Cosmos {
        kind: "x".to_owned(),
        size: f64::NAN,
        tilt: 1e9,
        arms: 99,
        rings: 99,
        moons: 99,
        planets: 0,
        bands: 99,
        glow: -3.0,
        theme: "?".to_owned(),
    };
    assert!(
        !compile_full(&compose_cosmos(&wild))
            .unwrap_or_default()
            .0
            .is_empty()
    );
    assert!(serde_json::from_str::<Cosmos>(r#"{"kind":"star","evil":1}"#).is_err());
}
