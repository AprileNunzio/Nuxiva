#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]

use nuxiva_sentinel_core::Day;
use nuxiva_sentinel_core::journal::Head;

use crate::Sighting;
use crate::index::IndexKey;
use crate::look::{Color, Item};
use crate::ops::{compact, erase, pin, relink};
use crate::retention::Policy;
use crate::search::Search;
use crate::sighting::{Class, Who};
use crate::store::{genesis, open_all, scan, seal};
use crate::tests::{OWNER, person};

const KEY: [u8; 32] = [9; 32];

fn day() -> Day {
    Day::parse("2026-11-06").unwrap()
}

fn index() -> IndexKey {
    IndexKey::derive(&[3; 32]).unwrap()
}

fn write(list: &[Sighting]) -> (Vec<u8>, Head) {
    let d = day();
    let idx = index();
    let mut head = genesis(&d);
    let mut data = Vec::new();
    for s in list {
        if let Ok((frame, next)) = seal(&KEY, &d, &head, &idx, s) {
            data.extend_from_slice(&frame);
            head = next;
        }
    }
    (data, head)
}

fn sample() -> Vec<Sighting> {
    let mut courier = person("aa112233445566778899aabbccddee01", Who::Unknown, 10_000);
    courier.look.hi_vis = Some(true);
    let owner = {
        let mut s = person(
            "aa112233445566778899aabbccddee02",
            Who::Person(OWNER.to_owned()),
            20_000,
        );
        s.look.upper = Some(Color::Green);
        s.look.carrying = vec![];
        s
    };
    let guest = person("aa112233445566778899aabbccddee03", Who::Guest(2), 30_000);
    vec![courier, owner, guest]
}

#[test]
fn seal_and_open_roundtrip() {
    let list = sample();
    let (data, head) = write(&list);
    let back = open_all(&KEY, &day(), &data).unwrap_or_default();
    assert_eq!(back, list);
    assert_eq!(scan(&day(), &data).map(|s| s.head).ok(), Some(head));
    assert!(!data.windows(9).any(|w| w == b"ingresso\""));
}

#[test]
fn tamper_is_detected() {
    let (mut data, _) = write(&sample());
    if let Some(b) = data.get_mut(80) {
        *b ^= 1;
    }
    assert!(open_all(&KEY, &day(), &data).is_err());
}

#[test]
fn wrong_key_or_day_fails() {
    let (data, _) = write(&sample());
    assert!(open_all(&[1; 32], &day(), &data).is_err());
    let other = Day::parse("2026-11-07").unwrap();
    assert!(open_all(&KEY, &other, &data).is_err());
}

#[test]
fn truncated_tail_is_reported() {
    let (data, _) = write(&sample());
    let cut = data.get(..data.len().saturating_sub(5)).unwrap_or_default();
    let s = scan(&day(), cut).ok();
    assert!(
        s.as_ref()
            .is_some_and(|s| s.truncated && s.frames.len() == 2)
    );
}

#[test]
fn search_by_look_opens_only_candidates() {
    let (data, _) = write(&sample());
    let q = Search {
        from_ms: 0,
        to_ms: 100_000,
        upper: Some(Color::Red),
        items: vec![Item::Parcel],
        limit: 10,
        ..Search::default()
    };
    let (hits, scanned, opened) = q.day(&KEY, &day(), &index(), &data).unwrap_or_default();
    assert_eq!(scanned, 3);
    assert_eq!(opened, 2);
    let page = q.page(hits, scanned, opened).ok();
    let ids: Vec<String> = page
        .map(|p| p.sightings.into_iter().map(|s| s.id).collect())
        .unwrap_or_default();
    assert_eq!(
        ids,
        vec![
            "aa112233445566778899aabbccddee03",
            "aa112233445566778899aabbccddee01"
        ]
    );
}

#[test]
fn search_hi_vis_and_class() {
    let (data, _) = write(&sample());
    let q = Search {
        from_ms: 0,
        to_ms: 100_000,
        hi_vis: Some(true),
        classes: vec![Class::Person],
        limit: 5,
        ..Search::default()
    };
    let (hits, _, opened) = q.day(&KEY, &day(), &index(), &data).unwrap_or_default();
    assert_eq!(opened, 1);
    assert_eq!(hits.len(), 1);
    let none = Search {
        classes: vec![Class::Vehicle],
        ..q
    };
    assert!(
        none.day(&KEY, &day(), &index(), &data)
            .unwrap()
            .0
            .is_empty()
    );
}

#[test]
fn search_validation() {
    assert!(
        Search {
            from_ms: 10,
            to_ms: 1,
            limit: 5,
            ..Search::default()
        }
        .validate()
        .is_err()
    );
    assert!(
        Search {
            from_ms: 0,
            to_ms: 1,
            limit: 0,
            ..Search::default()
        }
        .validate()
        .is_err()
    );
    assert!(
        Search {
            from_ms: 0,
            to_ms: 1,
            limit: 5,
            camera: Some("A B".to_owned()),
            ..Search::default()
        }
        .validate()
        .is_err()
    );
    assert!(
        Search {
            from_ms: 0,
            to_ms: 40 * 86_400_000,
            limit: 5,
            ..Search::default()
        }
        .validate()
        .is_err()
    );
}

#[test]
fn erase_removes_only_that_person() {
    let (data, _) = write(&sample());
    let who = Who::Person(OWNER.to_owned());
    let done = erase(&KEY, &day(), &index(), &data, &who).ok().flatten();
    let done = done.expect("erase");
    assert_eq!((done.count, done.changed), (2, 1));
    let back = open_all(&KEY, &day(), &done.data).unwrap_or_default();
    assert!(back.iter().all(|s| s.who != who));
    assert!(
        erase(&KEY, &day(), &index(), &done.data, &who)
            .ok()
            .flatten()
            .is_none()
    );
}

#[test]
fn relink_guest_to_person() {
    let (data, _) = write(&sample());
    let to = Who::Person("fedcba9876543210fedcba9876543210".to_owned());
    let done = relink(&KEY, &day(), &index(), &data, &Who::Guest(2), &to)
        .ok()
        .flatten();
    let done = done.expect("relink");
    assert_eq!(done.changed, 1);
    let q = Search {
        from_ms: 0,
        to_ms: 100_000,
        who: Some(to),
        limit: 5,
        ..Search::default()
    };
    assert_eq!(
        q.day(&KEY, &day(), &index(), &done.data)
            .map(|r| r.0.len())
            .ok(),
        Some(1)
    );
    assert!(relink(&KEY, &day(), &index(), &data, &Who::Guest(2), &Who::Unknown).is_err());
}

#[test]
fn compact_drops_strangers_first_and_keeps_pins() {
    let (data, _) = write(&sample());
    let pinned = pin(
        &KEY,
        &day(),
        &index(),
        &data,
        "aa112233445566778899aabbccddee01",
        true,
    )
    .ok()
    .flatten();
    let pinned = pinned.expect("pin");
    let done = compact(&KEY, &day(), &index(), &pinned.data, &Policy::default(), 2)
        .ok()
        .flatten();
    let done = done.expect("compact");
    let ids: Vec<String> = open_all(&KEY, &day(), &done.data)
        .unwrap_or_default()
        .into_iter()
        .map(|s| s.id)
        .collect();
    assert_eq!(
        ids,
        vec![
            "aa112233445566778899aabbccddee01",
            "aa112233445566778899aabbccddee02"
        ]
    );
    assert!(
        compact(&KEY, &day(), &index(), &done.data, &Policy::default(), 2)
            .ok()
            .flatten()
            .is_none()
    );
}
