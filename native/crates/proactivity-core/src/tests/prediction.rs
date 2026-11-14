use super::*;
use crate::{Forecast, Mode};

const WEEK: u64 = 7 * 24 * HOUR;

fn wake(e: &mut Engine, week: u64) {
    let at = DAY + week * WEEK + 9 * HOUR;
    e.ingest(
        &sig("schedule", "wake", Some("anna"), "anna", 1, at),
        &idle(&["anna"]),
        at,
    )
    .expect("wake");
}

#[test]
fn habit_predicts_before_the_event_once_enough_days_are_seen() {
    let mut e = engine();
    for w in 0..3 {
        wake(&mut e, w);
    }
    let t = DAY + 3 * WEEK + 8 * HOUR + 50 * MIN;
    let out = e.tick(&idle(&["anna"]), t).expect("tick");
    assert_eq!(out.len(), 1);
    assert_eq!(out[0].explanation.origin, "habit");
    assert_eq!(out[0].mode, Mode::Widget);
    assert_eq!(out[0].person.as_deref(), Some("anna"));
    assert!(
        out[0]
            .explanation
            .reasons
            .iter()
            .any(|r| r.code == "proactive.why.habit")
    );
    assert!(e.tick(&idle(&["anna"]), t + MIN).expect("again").is_empty());
}

#[test]
fn habit_needs_minimum_days() {
    let mut e = engine();
    for w in 0..2 {
        wake(&mut e, w);
    }
    let t = DAY + 2 * WEEK + 8 * HOUR + 50 * MIN;
    assert!(e.tick(&idle(&["anna"]), t).expect("tick").is_empty());
}

#[test]
fn habit_does_not_fire_at_an_unusual_hour() {
    let mut e = engine();
    for w in 0..4 {
        wake(&mut e, w);
    }
    let t = DAY + 4 * WEEK + 13 * HOUR;
    assert!(e.tick(&idle(&["anna"]), t).expect("tick").is_empty());
}

#[test]
fn habit_supports_the_live_signal_confidence() {
    let mut e = engine();
    for w in 0..4 {
        wake(&mut e, w);
    }
    let at = DAY + 4 * WEEK + 9 * HOUR;
    let out = e
        .ingest(
            &sig("schedule", "wake", Some("anna"), "anna", 1, at),
            &idle(&["anna"]),
            at,
        )
        .expect("ingest");
    assert!(
        out[0]
            .explanation
            .reasons
            .iter()
            .any(|r| r.code == "proactive.why.habit_support")
    );
}

#[test]
fn foresight_forecast_becomes_a_decision_with_the_probability_as_confidence() {
    let mut e = engine();
    let now = DAY + 12 * HOUR;
    let f = Engine::forecast_from_json(
        r#"{"rule":"meeting_soon","person":"anna","subject":"review","probability":720}"#,
    )
    .expect("forecast");
    let out = e.forecast(&f, &idle(&["anna"]), now).expect("run");
    assert_eq!(out[0].explanation.origin, "forecast");
    assert_eq!(out[0].confidence, 720);
    assert!(
        e.forecast(&f, &idle(&["anna"]), now + 1)
            .expect("dup")
            .is_empty()
    );
}

#[test]
fn weak_forecast_stays_silent() {
    let mut e = engine();
    let now = DAY + 12 * HOUR;
    let f = Forecast {
        rule: "meeting_soon".into(),
        person: Some("anna".into()),
        subject: "x".into(),
        probability: 300,
    };
    let out = e.forecast(&f, &idle(&["anna"]), now).expect("run");
    assert_eq!(out[0].mode, Mode::Diary);
}

#[test]
fn forecast_validation() {
    let mut e = engine();
    let now = DAY + 12 * HOUR;
    let unknown = Forecast {
        rule: "ghost".into(),
        person: None,
        subject: String::new(),
        probability: 500,
    };
    assert!(e.forecast(&unknown, &idle(&[]), now).is_err());
    let no_person = Forecast {
        rule: "meeting_soon".into(),
        person: None,
        subject: String::new(),
        probability: 500,
    };
    assert!(e.forecast(&no_person, &idle(&[]), now).is_err());
    let wild = Forecast {
        rule: "meeting_soon".into(),
        person: Some("anna".into()),
        subject: String::new(),
        probability: 5_000,
    };
    assert!(e.forecast(&wild, &idle(&[]), now).is_err());
    assert!(Engine::forecast_from_json(r#"{"rule":"x","probability":1,"extra":1}"#).is_err());
}
