#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]

use crate::index::IndexKey;
use crate::look::{Color, Headwear, Item, Look, Vehicle, VehicleKind};
use crate::profile::build;
use crate::retention::Policy;
use crate::sighting::{Audience, Class, Evidence, EvidenceKind, Sighting, Who};
use crate::store::Header;
use std::collections::BTreeMap;

pub fn person(id: &str, who: Who, start: u64) -> Sighting {
    Sighting {
        id: id.to_owned(),
        start_ms: start,
        end_ms: start.saturating_add(30_000),
        camera: "ingresso".to_owned(),
        zone: Some("porta".to_owned()),
        class: Class::Person,
        who,
        look: Look {
            upper: Some(Color::Red),
            lower: Some(Color::Blue),
            headwear: Some(Headwear::Cap),
            carrying: vec![Item::Parcel],
            height_cm: Some(178),
            glasses: Some(false),
            ..Look::default()
        },
        vehicle: None,
        gait: vec![0.5; 16],
        evidence: vec![Evidence {
            kind: EvidenceKind::Frame,
            id: "abcdef0123456789".to_owned(),
            at_ms: start,
        }],
        confidence: 0.9,
        pinned: false,
    }
}

pub const OWNER: &str = "0123456789abcdef0123456789abcdef";

#[test]
fn valid_sighting_passes() {
    assert!(
        person("00112233445566778899aabbccddeeff", Who::Unknown, 1000)
            .validate()
            .is_ok()
    );
}

#[test]
fn rejects_bad_fields() {
    let base = person("00112233445566778899aabbccddeeff", Who::Unknown, 1000);
    let mut s = base.clone();
    s.id = "XYZ".to_owned();
    assert!(s.validate().is_err());
    let mut s = base.clone();
    s.camera = "Ingresso/../x".to_owned();
    assert!(s.validate().is_err());
    let mut s = base.clone();
    s.gait = vec![f32::NAN; 16];
    assert!(s.validate().is_err());
    let mut s = base.clone();
    s.gait = vec![0.1; 3];
    assert!(s.validate().is_err());
    let mut s = base.clone();
    s.end_ms = 10;
    assert!(s.validate().is_err());
    let mut s = base.clone();
    s.look.carrying = vec![Item::Bag, Item::Bag];
    assert!(s.validate().is_err());
    let mut s = base.clone();
    s.look.height_cm = Some(400);
    assert!(s.validate().is_err());
    let mut s = base.clone();
    s.confidence = 1.5;
    assert!(s.validate().is_err());
    let mut s = base.clone();
    s.vehicle = Some(Vehicle {
        kind: VehicleKind::Van,
        color: None,
    });
    assert!(s.validate().is_err());
    let mut s = base;
    s.who = Who::Person("short".to_owned());
    assert!(s.validate().is_err());
}

#[test]
fn rejects_unknown_json_fields() {
    let raw = r#"{"id":"00112233445566778899aabbccddeeff","start_ms":1,"end_ms":2,"camera":"a","class":"person","who":{"type":"unknown"},"confidence":0.5,"plate":"AB123CD"}"#;
    assert!(serde_json::from_str::<Sighting>(raw).is_err());
}

#[test]
fn audience_follows_identity() {
    let id = "00112233445566778899aabbccddeeff";
    assert_eq!(
        person(id, Who::Person(OWNER.to_owned()), 1).audience(),
        Audience::Household
    );
    assert_eq!(person(id, Who::Guest(3), 1).audience(), Audience::Guest);
    assert_eq!(person(id, Who::Unknown, 1).audience(), Audience::Passerby);
    let mut v = person(id, Who::Unknown, 1);
    v.class = Class::Vehicle;
    v.vehicle = Some(Vehicle {
        kind: VehicleKind::Van,
        color: Some(Color::White),
    });
    assert_eq!(v.audience(), Audience::Object);
}

#[test]
fn tokens_are_keyed_and_stable() {
    let a = IndexKey::derive(&[7; 32]).unwrap();
    let b = IndexKey::derive(&[8; 32]).unwrap();
    let s = person("00112233445566778899aabbccddeeff", Who::Unknown, 1);
    assert_eq!(a.of(&s), a.of(&s));
    assert_ne!(a.of(&s), b.of(&s));
    assert!(IndexKey::derive(&[0; 32]).is_err());
    assert!(IndexKey::derive(&[1; 31]).is_err());
}

#[test]
fn policy_bounds_and_pins() {
    let mut over = BTreeMap::new();
    over.insert(Audience::Passerby, 8);
    assert!(Policy::with(&over).is_err());
    over.insert(Audience::Passerby, 0);
    assert!(Policy::with(&over).is_err());
    over.insert(Audience::Passerby, 7);
    let p = Policy::with(&over).unwrap();
    let stranger = Header {
        audience: Audience::Passerby,
        pinned: false,
        tokens: vec![],
    };
    assert!(p.keeps(&stranger, 6));
    assert!(!p.keeps(&stranger, 7));
    let pinned = Header {
        pinned: true,
        ..stranger
    };
    assert!(p.keeps(&pinned, 300));
    assert!(!Policy::default().keeps(
        &Header {
            audience: Audience::Guest,
            pinned: false,
            tokens: vec![]
        },
        1
    ));
}

#[test]
fn profile_summarises_habits() {
    let who = Who::Person(OWNER.to_owned());
    let mut list = vec![
        person("00112233445566778899aabbccddee01", who.clone(), 1000),
        person("00112233445566778899aabbccddee02", who.clone(), 5000),
    ];
    let mut third = person("00112233445566778899aabbccddee03", who, 9000);
    third.look.upper = Some(Color::Black);
    third.look.glasses = Some(true);
    third.look.height_cm = Some(180);
    list.push(third);
    let p = build(&list);
    assert_eq!(p.count, 3);
    assert_eq!(p.first_ms, Some(1000));
    assert_eq!(p.last_ms, Some(39_000));
    assert_eq!(p.upper.first(), Some(&(Color::Red, 2)));
    assert_eq!(p.height_cm, Some(178));
    assert!(p.glasses.is_some_and(|g| (g - 1.0 / 3.0).abs() < 1e-6));
    assert_eq!(p.gait_samples, 3);
    assert!(p.gait_signature.is_some());
}
