use super::*;
use crate::{Domain, Mode, PersonPolicy};

#[test]
fn private_health_is_blocked_with_guests_and_resurfaces_when_alone() {
    let mut e = engine();
    let now = DAY + 12 * HOUR;
    let crowd = ctx(Situation::Guests, &["anna"], true, false);
    let out = e
        .ingest(
            &sig("health", "heart_rate", Some("anna"), "anna", 150, now),
            &crowd,
            now,
        )
        .expect("ingest");
    assert_eq!(out[0].mode, Mode::Diary);
    assert!(out[0].deferred);
    assert!(out[0].subject.is_empty() || out[0].action.is_none());
    assert_eq!(e.stats().blocked, 1);
    assert!(e.pending().is_empty());
    let alone = e.tick(&idle(&["anna"]), now + MIN).expect("tick");
    assert_eq!(alone.len(), 1);
    assert_eq!(alone[0].mode, Mode::Widget);
    assert!(!alone[0].redacted);
}

#[test]
fn private_is_blocked_when_another_person_is_present() {
    let mut e = engine();
    let now = DAY + 12 * HOUR;
    let out = e
        .ingest(
            &sig("health", "heart_rate", Some("anna"), "anna", 150, now),
            &idle(&["anna", "luca"]),
            now,
        )
        .expect("ingest");
    assert!(out[0].deferred);
}

#[test]
fn private_is_blocked_when_the_subject_is_absent() {
    let mut e = engine();
    let now = DAY + 12 * HOUR;
    let out = e
        .ingest(
            &sig("health", "heart_rate", Some("anna"), "anna", 150, now),
            &idle(&["luca"]),
            now,
        )
        .expect("ingest");
    assert!(out[0].deferred);
}

#[test]
fn email_is_private_even_when_declared_less() {
    let mut e = engine();
    let now = DAY + 12 * HOUR;
    let out = e
        .ingest(
            &sig("email", "important", Some("anna"), "m1", 900, now),
            &idle(&["anna", "luca"]),
            now,
        )
        .expect("ingest");
    assert!(out[0].deferred);
}

#[test]
fn household_content_is_redacted_for_guests() {
    let mut e = engine();
    let now = DAY + 12 * HOUR;
    let crowd = ctx(Situation::Idle, &["anna"], true, true);
    let out = e
        .ingest(
            &sig(
                "calendar",
                "event_in_minutes",
                Some("anna"),
                "dentist",
                10,
                now,
            ),
            &crowd,
            now,
        )
        .expect("ingest");
    let d = &out[0];
    assert!(d.redacted);
    assert_eq!(d.mode, Mode::Widget);
    assert!(d.subject.is_empty());
    assert!(d.action.is_none());
    assert_eq!(d.summary_key, "proactive.redacted");
}

#[test]
fn redacted_explanation_never_leaks_the_subject() {
    let mut e = engine();
    let now = DAY + 12 * HOUR;
    let crowd = ctx(Situation::Idle, &["anna"], true, true);
    let out = e
        .ingest(
            &sig(
                "calendar",
                "event_in_minutes",
                Some("anna"),
                "dentist",
                10,
                now,
            ),
            &crowd,
            now,
        )
        .expect("ingest");
    let shown = serde_json::to_string(&out[0]).expect("json");
    assert!(!shown.contains("dentist"));
}

#[test]
fn person_can_mute_a_domain() {
    let mut e = engine();
    let mut policy = PersonPolicy::default();
    policy.muted.insert(Domain::Calendar);
    e.set_policy("anna", policy).expect("policy");
    let now = DAY + 12 * HOUR;
    let out = e
        .ingest(
            &sig("calendar", "event_in_minutes", Some("anna"), "a", 5, now),
            &idle(&["anna"]),
            now,
        )
        .expect("ingest");
    assert_eq!(out[0].mode, Mode::Diary);
    assert!(!out[0].deferred);
}

#[test]
fn sealing_a_domain_makes_it_private() {
    let mut e = engine();
    let mut policy = PersonPolicy::default();
    policy.sealed.insert(Domain::Calendar);
    e.set_policy("anna", policy).expect("policy");
    let now = DAY + 12 * HOUR;
    let out = e
        .ingest(
            &sig("calendar", "event_in_minutes", Some("anna"), "a", 5, now),
            &idle(&["anna", "luca"]),
            now,
        )
        .expect("ingest");
    assert!(out[0].deferred);
}

#[test]
fn critical_alerts_still_respect_privacy_but_security_is_household() {
    let mut e = engine();
    let now = DAY + 12 * HOUR;
    let crowd = ctx(Situation::Guests, &[], true, true);
    let out = e
        .ingest(
            &sig("security", "intrusion", None, "garage", 1, now),
            &crowd,
            now,
        )
        .expect("ingest");
    assert!(out[0].redacted);
    assert_ne!(out[0].mode, Mode::Diary);
    assert!(out[0].action.is_some());
    assert!(out[0].subject.is_empty());
}
