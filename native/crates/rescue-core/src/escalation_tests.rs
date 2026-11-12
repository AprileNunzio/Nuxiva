use crate::action::{Action, Stage, Tone};
use crate::escalation::{Engine, MAX_TIMELINE};
use crate::fusion_tests::ev;
use crate::policy::Policy;
use crate::signal::{Hazard, Kind};

fn engine() -> Engine {
    Engine::new(Policy::default())
}

fn feed(e: &mut Engine, kinds: &[(Kind, &str)], at: f64) {
    for (kind, source) in kinds {
        assert!(e.observe(ev(*kind, 0.9, 0.8, source, at), at).is_ok());
    }
}

fn has(actions: &[Action], pred: impl Fn(&Action) -> bool) -> bool {
    actions.iter().any(pred)
}

#[test]
fn calm_stays_calm() {
    let mut e = engine();
    let s = e.update(1.0);
    assert_eq!(s.stage, Stage::Calm);
    assert!(s.actions.is_empty());
}

#[test]
fn fall_then_stillness_asks_the_person_first() {
    let mut e = engine();
    feed(&mut e, &[(Kind::Fall, "cam1")], 0.0);
    assert_eq!(e.update(0.0).stage, Stage::Watching);
    feed(&mut e, &[(Kind::Immobility, "cam1")], 1.0);
    let s = e.update(1.0);
    assert_eq!(s.stage, Stage::CheckIn);
    assert_eq!(
        s.actions,
        vec![Action::AskPerson {
            hazard: Hazard::Medical,
            tone: Tone::Spoken
        }]
    );
    assert!(!has(&s.actions, |a| matches!(
        a,
        Action::AlertFamily { .. }
    )));
}

#[test]
fn person_ok_cancels_and_cools_down() {
    let mut e = engine();
    feed(
        &mut e,
        &[(Kind::Fall, "cam1"), (Kind::Immobility, "cam1")],
        0.0,
    );
    assert_eq!(e.update(0.0).stage, Stage::CheckIn);
    let s = e.person_ok(5.0);
    assert_eq!(s.stage, Stage::Cooldown);
    assert_eq!(
        s.actions,
        vec![Action::StandDown {
            hazard: Hazard::Medical,
            notified_tiers: 0,
            emergency: false
        }]
    );
    feed(
        &mut e,
        &[(Kind::Fall, "cam1"), (Kind::Immobility, "cam1")],
        10.0,
    );
    let again = e.update(10.0);
    assert!(again.actions.is_empty(), "{:?}", again.actions);
}

#[test]
fn cooldown_never_blocks_a_critical_signal() {
    let mut e = engine();
    feed(
        &mut e,
        &[(Kind::Fall, "cam1"), (Kind::Immobility, "cam1")],
        0.0,
    );
    e.update(0.0);
    e.person_ok(2.0);
    for (k, s) in [
        (Kind::Fall, "cam1"),
        (Kind::Immobility, "cam1"),
        (Kind::NoResponse, "voice"),
        (Kind::HelpWords, "mic1"),
        (Kind::Vitals, "watch"),
    ] {
        assert!(e.observe(ev(k, 0.99, 1.0, s, 3.0), 3.0).is_ok());
    }
    let s = e.update(3.0);
    assert_eq!(s.stage, Stage::Alerting);
    assert!(has(&s.actions, |a| matches!(
        a,
        Action::AlertFamily { tier: 0, .. }
    )));
}

#[test]
fn silence_escalates_tier_by_tier_then_emergency_bounded() {
    let mut e = engine();
    feed(
        &mut e,
        &[(Kind::Fall, "cam1"), (Kind::Immobility, "cam1")],
        0.0,
    );
    e.update(0.0);
    let s = e.update(31.0);
    assert_eq!(s.stage, Stage::Alerting);
    assert!(has(&s.actions, |a| matches!(
        a,
        Action::AlertFamily { tier: 0, .. }
    )));
    assert!(has(&s.actions, |a| matches!(
        a,
        Action::RemindEmergencyNumber { .. }
    )));
    let s = e.update(31.0 + 121.0);
    assert!(has(&s.actions, |a| matches!(
        a,
        Action::AlertFamily { tier: 1, .. }
    )));
    let s = e.update(31.0 + 242.0);
    assert_eq!(s.stage, Stage::Emergency);
    assert!(has(&s.actions, |a| matches!(
        a,
        Action::AlertEmergencyContacts { round: 1, .. }
    )));
    let mut rounds = 1;
    for i in 1..20 {
        let s = e.update(31.0 + 242.0 + 181.0 * f64::from(i));
        rounds += s
            .actions
            .iter()
            .filter(|a| matches!(a, Action::AlertEmergencyContacts { .. }))
            .count();
    }
    assert_eq!(rounds, usize::from(Policy::default().emergency_rounds));
}

#[test]
fn check_in_closes_quietly_when_risk_vanished() {
    let mut e = engine();
    feed(
        &mut e,
        &[(Kind::Scream, "mic1"), (Kind::HelpWords, "mic1")],
        0.0,
    );
    assert_eq!(e.update(0.0).stage, Stage::CheckIn);
    let s = e.update(400.0);
    assert_eq!(s.stage, Stage::Cooldown);
    assert!(!has(&s.actions, |a| matches!(
        a,
        Action::AlertFamily { .. }
    )));
}

#[test]
fn acknowledgement_stops_escalation() {
    let mut e = engine();
    let s = e.need_help(0.0);
    assert_eq!(s.stage, Stage::Alerting);
    assert!(has(&s.actions, |a| matches!(
        a,
        Action::AlertFamily { tier: 0, .. }
    )));
    let s = e.acknowledge(0, 10.0);
    assert_eq!(s.stage, Stage::Acknowledged);
    assert!(e.update(5000.0).actions.is_empty());
    let s = e.person_ok(5001.0);
    assert!(has(&s.actions, |a| matches!(
        a,
        Action::StandDown {
            notified_tiers: 1,
            ..
        }
    )));
}

#[test]
fn explicit_help_while_alerting_jumps_a_tier() {
    let mut e = engine();
    e.need_help(0.0);
    let s = e.need_help(3.0);
    assert!(has(&s.actions, |a| matches!(
        a,
        Action::AlertFamily { tier: 1, .. }
    )));
}

#[test]
fn smoke_sounds_the_alarm_without_waiting() {
    let mut e = engine();
    assert!(
        e.observe(ev(Kind::Smoke, 0.95, 1.0, "ha.smoke", 0.0), 0.0)
            .is_ok()
    );
    let s = e.update(0.0);
    assert_eq!(s.hazard, Some(Hazard::Fire));
    assert!(has(&s.actions, |a| matches!(a, Action::HomeAlarm { .. })));
    assert!(has(&s.actions, |a| matches!(
        a,
        Action::AlertFamily { tier: 0, .. }
    )));
    assert!(e.person_ok(1.0).actions.is_empty());
    assert_eq!(e.stage(), Stage::Alerting);
    let s = e.dismiss(2.0);
    assert!(has(&s.actions, |a| matches!(
        a,
        Action::StandDown {
            hazard: Hazard::Fire,
            ..
        }
    )));
}

#[test]
fn fire_during_medical_incident_is_raised_too() {
    let mut e = engine();
    feed(
        &mut e,
        &[(Kind::Fall, "cam1"), (Kind::Immobility, "cam1")],
        0.0,
    );
    e.update(0.0);
    assert!(
        e.observe(ev(Kind::Fire, 0.95, 1.0, "ha.heat", 1.0), 1.0)
            .is_ok()
    );
    let s = e.update(1.0);
    assert!(has(&s.actions, |a| matches!(
        a,
        Action::HomeAlarm {
            hazard: Hazard::Fire
        }
    )));
}

#[test]
fn intrusion_is_discreet() {
    let mut e = engine();
    for s in ["cam1", "cam2"] {
        assert!(
            e.observe(ev(Kind::Intrusion, 0.9, 0.9, s, 0.0), 0.0)
                .is_ok()
        );
    }
    let s = e.update(0.0);
    assert!(s.stage.active());
    assert!(s.actions.iter().all(|a| !matches!(
        a,
        Action::AskPerson {
            tone: Tone::Spoken,
            ..
        } | Action::HomeAlarm { .. }
    )));
}

#[test]
fn violence_alone_never_alerts_family_directly() {
    let mut e = engine();
    assert!(
        e.observe(ev(Kind::Violence, 0.9, 0.9, "mic1", 0.0), 0.0)
            .is_ok()
    );
    let s = e.update(0.0);
    assert!(!has(&s.actions, |a| matches!(
        a,
        Action::AlertFamily { .. }
    )));
}

#[test]
fn timeline_is_bounded_and_incidents_count() {
    let mut e = engine();
    for i in 0..200 {
        let t = f64::from(i) * 1000.0;
        e.need_help(t);
        e.person_ok(t + 1.0);
    }
    assert!(e.timeline().len() <= MAX_TIMELINE);
    let s = e.need_help(1e6);
    assert_eq!(s.incident, 201);
}

#[test]
fn evidence_store_is_bounded() {
    let mut e = engine();
    for i in 0..2000 {
        let src = format!("cam{i}");
        assert!(e.observe(ev(Kind::Fall, 0.6, 0.5, &src, 0.0), 0.0).is_ok());
    }
    assert!(e.evidence_count() <= crate::signal::MAX_EVIDENCE);
}
