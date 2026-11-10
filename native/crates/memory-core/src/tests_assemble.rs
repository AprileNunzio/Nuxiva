#![allow(
    clippy::unwrap_used,
    clippy::expect_used,
    clippy::panic,
    clippy::indexing_slicing
)]

use crate::assemble::{Assembler, Observation};
use crate::episode::{EpisodeKind, detect};
use crate::look::{Color, Item, Look, Vehicle, VehicleKind};
use crate::sighting::{Class, Who};
use crate::tests::OWNER;

fn obs(at: u64, class: Class, x: f32, who: Option<Who>) -> Observation {
    Observation {
        camera: "ingresso".to_owned(),
        at_ms: at,
        class,
        bbox: [x, 0.2, 0.2, 0.6],
        track: None,
        zone: Some("porta".to_owned()),
        who,
        look: Look {
            upper: Some(Color::Red),
            carrying: vec![Item::Parcel],
            hi_vis: Some(true),
            height_cm: Some(180),
            ..Look::default()
        },
        vehicle: (class == Class::Vehicle).then_some(Vehicle {
            kind: VehicleKind::Van,
            color: Some(Color::White),
        }),
        evidence: None,
        score: 0.9,
    }
}

#[test]
fn moving_person_becomes_one_sighting() {
    let mut a = Assembler::new(10_000, 600_000);
    for (i, x) in [0.10_f32, 0.15, 0.20, 0.26].iter().enumerate() {
        assert_eq!(
            a.push(&obs(1_000 * i as u64, Class::Person, *x, None))
                .unwrap(),
            [] as [crate::sighting::Sighting; 0]
        );
    }
    assert_eq!(a.flush(5_000), [] as [crate::sighting::Sighting; 0]);
    let done = a.flush(20_000);
    assert_eq!(done.len(), 1);
    let s = &done[0];
    assert_eq!((s.start_ms, s.end_ms), (0, 3_000));
    assert_eq!(s.look.upper, Some(Color::Red));
    assert_eq!(s.look.carrying, vec![Item::Parcel]);
    assert!(s.validate().is_ok());
}

#[test]
fn far_apart_people_stay_separate() {
    let mut a = Assembler::new(10_000, 600_000);
    a.push(&obs(0, Class::Person, 0.0, None)).unwrap();
    a.push(&obs(500, Class::Person, 0.7, None)).unwrap();
    assert_eq!(a.open_count(), 2);
}

#[test]
fn identity_needs_a_clear_majority() {
    let mut a = Assembler::new(10_000, 600_000);
    let owner = Who::Person(OWNER.to_owned());
    for i in 0..4 {
        a.push(&obs(i * 1000, Class::Person, 0.1, Some(owner.clone())))
            .unwrap();
    }
    assert_eq!(a.drain()[0].who, owner);
    let mut b = Assembler::new(10_000, 600_000);
    b.push(&obs(0, Class::Person, 0.1, Some(owner.clone())))
        .unwrap();
    b.push(&obs(1000, Class::Person, 0.1, Some(Who::Guest(3))))
        .unwrap();
    assert_eq!(b.drain()[0].who, Who::Unknown);
}

#[test]
fn invalid_observations_are_rejected() {
    let mut a = Assembler::new(10_000, 600_000);
    let mut o = obs(0, Class::Person, 0.1, None);
    o.bbox = [f32::NAN, 0.0, 0.1, 0.1];
    assert!(a.push(&o).is_err());
    let mut o = obs(0, Class::Person, 0.1, None);
    o.camera = "Camera 1".to_owned();
    assert!(a.push(&o).is_err());
    let mut o = obs(0, Class::Vehicle, 0.1, None);
    o.vehicle = None;
    assert!(a.push(&o).is_err());
}

#[test]
fn courier_with_van_is_a_delivery() {
    let mut a = Assembler::new(5_000, 600_000);
    a.push(&obs(0, Class::Vehicle, 0.6, None)).unwrap();
    a.push(&obs(60_000, Class::Person, 0.1, None)).unwrap();
    a.push(&obs(61_000, Class::Person, 0.12, None)).unwrap();
    let all = a.drain();
    let eps = detect(&all);
    let delivery = eps
        .iter()
        .find(|e| e.kind == EpisodeKind::Delivery)
        .expect("delivery");
    assert!(delivery.reasons.contains(&"delivery_vehicle"));
    assert!(delivery.reasons.contains(&"parcel_in_hand"));
    assert_eq!(delivery.sightings.len(), 2);
    assert!(delivery.confidence > 0.5 && delivery.confidence <= 0.95);
}

#[test]
fn household_member_is_never_a_courier() {
    let mut a = Assembler::new(5_000, 600_000);
    let owner = Who::Person(OWNER.to_owned());
    a.push(&obs(0, Class::Person, 0.1, Some(owner.clone())))
        .unwrap();
    a.push(&obs(1000, Class::Person, 0.1, Some(owner))).unwrap();
    assert_eq!(detect(&a.drain()), [] as [crate::episode::Episode; 0]);
}

#[test]
fn masked_stranger_is_flagged() {
    let mut a = Assembler::new(5_000, 600_000);
    let mut o = obs(0, Class::Person, 0.1, None);
    o.look = Look {
        face_covered: Some(true),
        ..Look::default()
    };
    a.push(&o).unwrap();
    let eps = detect(&a.drain());
    assert_eq!(
        eps.iter().map(|e| e.kind).collect::<Vec<_>>(),
        vec![EpisodeKind::MaskedPerson]
    );
}
