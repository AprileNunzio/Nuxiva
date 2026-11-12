use std::collections::BTreeMap;

use crate::event::{Event, Narrative, Sensitivity, Subject};
use crate::kind::{ALL, Group, Kind};
use crate::query::Query;
use crate::retention::Retention;

pub const ANNA: &str = "a1b2c3d4e5f60718293a4b5c6d7e8f90";
const DAY: u64 = 86_400_000;
type Mutation = Box<dyn Fn(&mut Event)>;

pub fn event(n: u64, kind: Kind, subject: Subject) -> Event {
    Event {
        id: format!("{n:016x}"),
        at_ms: 1_800_000_000_000_u64.saturating_add(n.saturating_mul(1000)),
        kind,
        subject,
        place: Some("salotto".to_owned()),
        narrative: Narrative {
            key: "sentinel.presence.arrived".to_owned(),
            params: BTreeMap::from([("person".to_owned(), "Anna".to_owned())]),
        },
        sensitivity: Sensitivity::Personal,
        source: "presence".to_owned(),
        links: Vec::new(),
    }
}

#[test]
fn every_kind_has_a_dotted_name_and_a_group() {
    for kind in ALL {
        let name = kind.name();
        assert!(name.contains('.'), "{kind:?}");
        let back: Kind = match serde_json::from_value(serde_json::Value::String(name)) {
            Ok(k) => k,
            Err(e) => unreachable!("{e}"),
        };
        assert_eq!(back, kind);
    }
    assert_eq!(Kind::GuestAppearance.group(), Group::GuestAppearance);
    assert_eq!(Kind::AccessDenied.group(), Group::Denied);
}

#[test]
fn events_are_validated() {
    assert!(
        event(1, Kind::PresenceArrived, Subject::Person(ANNA.to_owned()))
            .validate()
            .is_ok()
    );
    let cases: Vec<Mutation> = vec![
        Box::new(|e| e.id = "xyz".to_owned()),
        Box::new(|e| e.subject = Subject::Person("Anna".to_owned())),
        Box::new(|e| e.subject = Subject::Guest(0)),
        Box::new(|e| e.narrative.key = "evil.key".to_owned()),
        Box::new(|e| {
            e.narrative
                .params
                .insert("x".to_owned(), "a\u{0}b".to_owned());
        }),
        Box::new(|e| {
            e.narrative
                .params
                .insert("Bad Key".to_owned(), "v".to_owned());
        }),
        Box::new(|e| e.place = Some("../etc".to_owned())),
        Box::new(|e| e.links = vec!["00".to_owned()]),
    ];
    for (i, mutate) in cases.iter().enumerate() {
        let mut e = event(1, Kind::PresenceArrived, Subject::Nuxiva);
        mutate(&mut e);
        assert!(e.validate().is_err(), "case {i}");
    }
}

#[test]
fn retention_follows_the_group_and_respects_caps() {
    let r = Retention::default();
    let mut e = event(0, Kind::GuestAppearance, Subject::Guest(1));
    assert!(r.keeps(&e, e.at_ms.saturating_add(DAY / 2)));
    assert!(!r.keeps(&e, e.at_ms.saturating_add(DAY)));
    e.kind = Kind::AccessDenied;
    assert!(r.keeps(&e, e.at_ms.saturating_add(179 * DAY)));
    assert!(Retention::with(&BTreeMap::from([(Group::GuestAppearance, 30)])).is_err());
    assert!(Retention::with(&BTreeMap::from([(Group::Presence, 0)])).is_err());
    assert_eq!(
        Retention::with(&BTreeMap::from([(Group::Presence, 60)])).map(|r| r.days(Group::Presence)),
        Ok(60)
    );
    assert!(r.day_expired(0, 180 * DAY));
    assert!(!r.day_expired(0, 179 * DAY));
}

#[test]
fn queries_filter_page_and_bound_the_range() {
    let events: Vec<Event> = (0..10_u64)
        .map(|n| {
            let kind = if n % 2 == 0 {
                Kind::PresenceArrived
            } else {
                Kind::AutomationStarted
            };
            let subject = if n % 2 == 0 {
                Subject::Person(ANNA.to_owned())
            } else {
                Subject::Automation("casa".to_owned())
            };
            event(n, kind, subject)
        })
        .collect();
    let base = 1_800_000_000_000_u64;
    let q = Query {
        from_ms: base,
        to_ms: base.saturating_add(DAY),
        groups: vec![Group::Presence],
        subject: None,
        limit: 3,
        before: None,
    };
    let Ok(page) = q.run(events.clone()) else {
        unreachable!()
    };
    assert_eq!(page.events.len(), 3);
    assert!(
        page.events
            .windows(2)
            .all(|w| matches!(w, [a, b] if a.at_ms > b.at_ms))
    );
    let Ok(rest) = Query {
        before: page.next.clone(),
        ..q.clone()
    }
    .run(events.clone()) else {
        unreachable!()
    };
    assert_eq!(rest.events.len(), 2);
    assert!(rest.next.is_none());
    let by_subject = Query {
        groups: vec![],
        subject: Some("automation:casa".to_owned()),
        limit: 200,
        ..q.clone()
    };
    assert_eq!(
        by_subject.run(events.clone()).map(|p| p.events.len()),
        Ok(5)
    );
    assert!(
        Query {
            to_ms: base.saturating_add(32 * DAY),
            ..q.clone()
        }
        .validate()
        .is_err()
    );
    assert!(
        Query {
            limit: 201,
            ..q.clone()
        }
        .validate()
        .is_err()
    );
    assert!(Query { to_ms: 0, ..q }.validate().is_err());
}
