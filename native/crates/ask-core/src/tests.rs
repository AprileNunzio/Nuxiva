#![allow(
    clippy::unwrap_used,
    clippy::expect_used,
    clippy::panic,
    clippy::indexing_slicing
)]

use nuxiva_memory_core::{
    Class, Color, Evidence, EvidenceKind, Item, Look, Sighting, Vehicle, Who,
};

use crate::error::AskError;
use crate::evidence::format_time_hh_mm;
use crate::parser::parse;
use crate::query::{QueryLang, QuestionKind, RoleTarget};
use crate::{ask, evaluate};

fn sample_sighting(
    id: &str,
    start_ms: u64,
    camera: &str,
    class: Class,
    upper: Option<Color>,
    items: Vec<Item>,
    vehicle: Option<Vehicle>,
) -> Sighting {
    Sighting {
        id: id.to_owned(),
        start_ms,
        end_ms: start_ms.saturating_add(60_000),
        camera: camera.to_owned(),
        zone: Some("ingresso".to_owned()),
        class,
        who: Who::Unknown,
        look: Look {
            upper,
            lower: None,
            headwear: None,
            face_covered: None,
            glasses: None,
            beard: None,
            hi_vis: Some(items.contains(&Item::Parcel)),
            build: None,
            height_cm: Some(175),
            carrying: items,
        },
        vehicle,
        gait: Vec::new(),
        evidence: vec![
            Evidence {
                kind: EvidenceKind::Frame,
                id: format!("frame_{id}"),
                at_ms: start_ms,
            },
            Evidence {
                kind: EvidenceKind::Clip,
                id: format!("clip_{id}"),
                at_ms: start_ms,
            },
        ],
        confidence: 0.92,
        pinned: false,
    }
}

#[test]
fn test_parse_empty() {
    assert!(matches!(parse("", 1_000_000), Err(AskError::EmptyQuery)));
    assert!(matches!(parse("   ", 1_000_000), Err(AskError::EmptyQuery)));
}

#[test]
fn test_parse_italian_courier() {
    let now = 1_700_000_000_000_u64;
    let q = parse(
        "a che ora è venuto il corriere ieri e com'era vestito?",
        now,
    )
    .unwrap();
    assert_eq!(q.lang, QueryLang::It);
    assert_eq!(q.kind, QuestionKind::When);
    assert_eq!(q.target_role, Some(RoleTarget::Courier));
    assert_eq!(q.class, Some(Class::Person));
    assert!(q.from_ms < q.to_ms);
}

#[test]
fn test_parse_english_red_jacket() {
    let now = 1_700_000_000_000_u64;
    let q = parse("did you see someone wearing a red jacket yesterday?", now).unwrap();
    assert_eq!(q.lang, QueryLang::En);
    assert_eq!(q.upper_color, Some(Color::Red));
    assert_eq!(q.class, Some(Class::Person));
}

#[test]
fn test_parse_french_delivery() {
    let now = 1_700_000_000_000_u64;
    let q = parse("à quelle heure est venu le livreur hier?", now).unwrap();
    assert_eq!(q.lang, QueryLang::Fr);
    assert_eq!(q.kind, QuestionKind::When);
    assert_eq!(q.target_role, Some(RoleTarget::Courier));
}

#[test]
fn test_parse_spanish_car() {
    let now = 1_700_000_000_000_u64;
    let q = parse("¿has visto un coche blanco hoy?", now).unwrap();
    assert_eq!(q.lang, QueryLang::Es);
    assert_eq!(q.class, Some(Class::Vehicle));
    assert_eq!(q.vehicle_color, Some(Color::White));
}

#[test]
fn test_evaluate_and_citations() {
    let now = 1_700_000_000_000_u64;
    let yesterday_ms = now.saturating_sub(100_000_000);

    let courier = sample_sighting(
        "s1",
        yesterday_ms,
        "cancello",
        Class::Person,
        Some(Color::Red),
        vec![Item::Parcel],
        None,
    );

    let bystander = sample_sighting(
        "s2",
        yesterday_ms.saturating_sub(3_600_000),
        "strada",
        Class::Person,
        Some(Color::Blue),
        Vec::new(),
        None,
    );

    let sightings = vec![courier, bystander];
    let ans = ask(
        "a che ora è venuto il corriere ieri e com'era vestito?",
        now,
        &sightings,
    )
    .unwrap();

    assert!(ans.found);
    assert_eq!(ans.citations.len(), 1);
    let first = ans.citations.first().unwrap();
    assert_eq!(first.sighting_id, "s1");
    assert_eq!(first.camera, "cancello");
    assert_eq!(first.frame_evidence_id.as_deref(), Some("frame_s1"));
    assert_eq!(first.clip_evidence_id.as_deref(), Some("clip_s1"));
    assert!(ans.summary.contains("cancello"));
    assert!(ans.summary.contains("Prove:"));
    assert!(ans.summary.contains("frame_s1"));
}

#[test]
fn test_evaluate_no_match() {
    let now = 1_700_000_000_000_u64;
    let query = parse("è passata un'auto oggi?", now).unwrap();
    let ans = evaluate(&query, &[]);
    assert!(!ans.found);
    assert_eq!(ans.citations.len(), 0);
    assert!(ans.summary.contains("Nessuna prova"));
}

#[test]
fn test_time_formatter() {
    let ms = 14 * 3600 * 1000 + 25 * 60 * 1000;
    assert_eq!(format_time_hh_mm(ms), "14:25");
}
