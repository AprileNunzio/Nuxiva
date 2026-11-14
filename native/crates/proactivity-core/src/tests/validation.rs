use super::*;
use crate::{ProactivityError, Ruleset, Settings};

fn mutate(from: &str, to: &str) -> Result<Ruleset, ProactivityError> {
    Ruleset::from_json(&RULES.replacen(from, to, 1))
}

#[test]
fn reference_rules_are_valid() {
    assert!(Ruleset::from_json(RULES).is_ok());
}

#[test]
fn doors_payments_and_destructive_kinds_are_forbidden() {
    for kind in [
        "door.unlock",
        "lock.open",
        "unlock_all",
        "payment.send",
        "delete.files",
        "wipe.disk",
    ] {
        assert!(mutate("calendar.prepare", kind).is_err(), "{kind}");
    }
    assert!(mutate("lights.off", "door.open").is_err());
}

#[test]
fn automatic_execution_needs_low_risk_undo_and_normal_urgency() {
    assert!(
        mutate(
            r#""level":"do_and_tell","base_confidence":900"#,
            r#""level":"do_and_tell","base_confidence":900"#
        )
        .is_ok()
    );
    let no_undo = RULES.replacen(
        ",\n  \"undo\":{\"kind\":\"lights.off\",\"input_template\":\"room:{subject}\",\"window_ms\":600000}",
        "",
        1,
    );
    assert!(Ruleset::from_json(&no_undo).is_err());
    let risky = RULES.replacen(
        r#""risk_max":"low","input_template":"room:{subject}""#,
        r#""risk_max":"medium","input_template":"room:{subject}""#,
        1,
    );
    assert!(Ruleset::from_json(&risky).is_err());
}

#[test]
fn malformed_rules_are_rejected() {
    assert!(mutate(r#""base_confidence":800"#, r#""base_confidence":5000"#).is_err());
    assert!(mutate(r#""cmp":"present""#, r#""cmp":"absent""#).is_err());
    assert!(mutate("calendar.prepare", "Calendar Prepare").is_err());
    assert!(mutate(r#""wall_ms":30000"#, r#""wall_ms":0"#).is_err());
    assert!(Ruleset::from_json("{").is_err());
    assert!(Ruleset::from_json(r#"{"rules":{}}"#).is_err());
    assert!(Ruleset::from_json(&RULES.replacen("\"rules\"", "\"extra\":1,\"rules\"", 1)).is_err());
    assert!(Ruleset::from_json(&"x".repeat(crate::MAX_PAYLOAD + 1)).is_err());
}

#[test]
fn settings_are_validated() {
    assert!(Settings::default().validate().is_ok());
    let mut s = Settings::default();
    s.cost_conversation = 500;
    assert!(s.validate().is_err());
    let mut s = Settings::default();
    s.person_hourly_cap = s.hourly_cap + 1;
    assert!(s.validate().is_err());
    assert!(Settings::from_json(r#"{"hourly_cap":1}"#).is_err());
    let json = serde_json::to_string(&Settings::default()).expect("json");
    assert_eq!(
        Settings::from_json(&json).expect("round"),
        Settings::default()
    );
}

#[test]
fn hostile_runtime_input_is_refused() {
    let mut e = engine();
    let now = DAY + 12 * HOUR;
    let c = idle(&["anna"]);
    let mut bad = sig("calendar", "event_in_minutes", Some("anna"), "x", 5, now);
    bad.subject = "line\nbreak".into();
    assert!(e.ingest(&bad, &c, now).is_err());
    let mut bad = sig("calendar", "event_in_minutes", Some("anna"), "x", 5, now);
    bad.key = "BAD KEY".into();
    assert!(e.ingest(&bad, &c, now).is_err());
    let mut bad = sig("calendar", "event_in_minutes", Some("a|b"), "x", 5, now);
    bad.person = Some("a|b".into());
    assert!(e.ingest(&bad, &c, now).is_err());
    let mut bad_ctx = idle(&["anna"]);
    bad_ctx.tz_offset_min = 5_000;
    assert!(e.tick(&bad_ctx, now).is_err());
    assert!(Engine::signal_from_json(&"x".repeat(9_000)).is_err());
    assert!(Engine::signal_from_json(r#"{"domain":"home","key":"k","at":1,"zzz":1}"#).is_err());
    assert!(Engine::signal_from_json(r#"{"domain":"nowhere","key":"k","at":1}"#).is_err());
}

#[test]
fn unknown_ids_are_not_found() {
    let mut e = engine();
    assert_eq!(e.accept(9, 0), Err(ProactivityError::NotFound));
    assert_eq!(e.refuse(9, 0), Err(ProactivityError::NotFound));
    assert_eq!(e.undo(9, 0), Err(ProactivityError::NotFound));
    assert!(e.explain(9).is_err());
    assert!(ProactivityError::from_code("proactivity.consent").is_some());
}
