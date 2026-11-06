use std::collections::{HashMap, HashSet};

use crate::{CRITICAL_CAP, HomeRules, HomeTables, MAX_TARGETS, Risk, Target};

fn set(items: &[&str]) -> HashSet<String> {
    items.iter().map(|s| (*s).to_owned()).collect()
}

fn rules() -> HomeRules {
    let domains: HashMap<String, Risk> = [
        ("light", Risk::Home),
        ("cover", Risk::Home),
        ("lock", Risk::Personal),
        ("climate", Risk::Personal),
        ("script", Risk::Files),
    ]
    .into_iter()
    .map(|(k, v)| (k.to_owned(), v))
    .collect();
    HomeRules::new(HomeTables {
        domains,
        unknown: Risk::Files,
        read_private: set(&["person", "lock"]),
        sensitive_covers: set(&["garage", "gate", "door"]),
        appliances: set(&["switch"]),
        climate: set(&["climate"]),
        gate_open: set(&["open_cover", "set_cover_position", "toggle", "stop_cover"]),
        comfort: (18.0, 24.0),
    })
}

fn t<'a>(domain: &'a str, device_class: &'a str) -> Target<'a> {
    Target {
        domain,
        device_class,
    }
}

#[test]
fn service_risk_marks_sensitive_actions_critical() {
    let r = rules();
    assert_eq!(
        r.call_risk("light", "turn_on", &[t("light", "")]),
        Risk::Home
    );
    assert_eq!(
        r.call_risk("lock", "unlock", &[t("lock", "")]),
        Risk::Critical
    );
    assert_eq!(
        r.call_risk("cover", "open_cover", &[t("cover", "garage")]),
        Risk::Critical
    );
    assert_eq!(
        r.call_risk("cover", "close_cover", &[t("cover", "garage")]),
        Risk::Personal
    );
    assert_eq!(
        r.call_risk("cover", "open_cover", &[t("cover", "curtain")]),
        Risk::Home
    );
    assert_eq!(r.call_risk("valve", "open_valve", &[]), Risk::Critical);
    assert_eq!(
        r.call_risk("light", "turn_on", &[t("script", "")]),
        Risk::Files
    );
    assert_eq!(r.call_risk("", "turn_on", &[]), Risk::Files);
}

#[test]
fn oversized_requests_fail_closed() {
    let r = rules();
    let many = vec![t("light", ""); MAX_TARGETS + 1];
    assert_eq!(r.call_risk("light", "turn_on", &many), Risk::Critical);
    let long = "x".repeat(300);
    assert_eq!(r.call_risk(&long, "turn_on", &[]), Risk::Critical);
    assert_eq!(
        r.call_capabilities("light", &long, &[], None),
        vec![CRITICAL_CAP]
    );
    assert_eq!(r.read_risk(&[long.as_str()]), Risk::Critical);
}

#[test]
fn capabilities_follow_domain_and_comfort() {
    let r = rules();
    assert_eq!(
        r.capability("cover", "toggle", "gate", None),
        "home.gate.open"
    );
    assert_eq!(
        r.capability("cover", "close_cover", "gate", None),
        "home.gate.close"
    );
    assert_eq!(
        r.capability("alarm_control_panel", "alarm_arm_away", "", None),
        "home.alarm.arm"
    );
    assert_eq!(
        r.capability("climate", "set_temperature", "", Some(21.0)),
        "home.climate.adjust"
    );
    assert_eq!(
        r.capability("climate", "set_temperature", "", Some(f64::NAN)),
        "home.climate.set"
    );
    assert_eq!(
        r.capability("climate", "set_temperature", "", Some(30.0)),
        "home.climate.set"
    );
    assert_eq!(
        r.capability("switch", "turn_on", "", None),
        "home.appliance.set"
    );
    assert_eq!(r.capability("mystery", "x", "", None), CRITICAL_CAP);
    assert_eq!(
        r.call_capabilities("light", "turn_on", &[t("lock", ""), t("lock", "")], None),
        vec!["home.light.set", "home.lock.unlock"]
    );
    assert_eq!(r.read_capability(&["person"]), "home.private.read");
    assert_eq!(r.read_capability(&["sensor"]), "home.state.read");
    assert_eq!(r.read_risk(&["lock", "sensor"]), Risk::Personal);
}
