use crate::model::{ActionKind, Autonomy, Input, Mode, Origin, Posture, Severity, Stage};
use crate::{GeoTable, assess, assess_json, incident, net};

fn input(alerts: serde_json::Value) -> Input {
    let mut raw = serde_json::Map::new();
    raw.insert("now".into(), serde_json::json!(10_000.0));
    raw.insert("alerts".into(), alerts);
    let raw = serde_json::Value::Object(raw);
    serde_json::from_value(raw).unwrap_or_default()
}

fn alert(kind: &str, severity: &str, src: &str, at: f64) -> serde_json::Value {
    serde_json::json!({"kind": kind, "severity": severity, "src": src, "dst": "192.168.1.10", "count": 3, "at": at})
}

#[test]
fn groups_alerts_by_source_into_incidents() {
    let data = input(serde_json::json!([
        alert("port_scan", "medium", "8.8.4.4", 9_900.0),
        alert("brute_force", "high", "8.8.4.4", 9_950.0),
        alert("port_scan", "low", "192.168.1.50", 9_990.0),
    ]));
    let out = assess(&data);
    assert_eq!(out.incidents.len(), 2);
    let first = out
        .incidents
        .first()
        .map(|i| (i.src.as_str(), i.stage, i.origin, i.alerts));
    assert_eq!(
        first,
        Some(("8.8.4.4", Stage::Intrusion, Origin::Internet, 2))
    );
    assert_eq!(out.internet, 1);
    assert_eq!(out.lan, 1);
}

#[test]
fn old_alerts_fall_outside_the_window() {
    let data = input(serde_json::json!([alert(
        "port_scan",
        "high",
        "8.8.4.4",
        1.0
    )]));
    assert!(assess(&data).incidents.is_empty());
    assert_eq!(assess(&data).posture, Posture::Calm);
}

#[test]
fn trusted_and_protected_sources_only_warn() {
    let mut data = input(serde_json::json!([
        alert("brute_force", "critical", "203.0.113.7", 9_990.0),
        alert("brute_force", "critical", "198.51.100.1", 9_990.0),
    ]));
    data.trusted = vec!["203.0.113.0/24".into()];
    data.protected = vec!["198.51.100.1".into()];
    data.policy.mode = Mode::Protect;
    data.policy.autonomy = Autonomy::Autonomous;
    let out = assess(&data);
    assert!(
        out.actions
            .iter()
            .all(|a| a.kind == ActionKind::Warn && !a.auto)
    );
    assert_eq!(out.actions.len(), 2);
}

#[test]
fn monitor_mode_never_acts_automatically() {
    let mut data = input(serde_json::json!([alert(
        "brute_force",
        "critical",
        "8.8.8.8",
        9_990.0
    )]));
    data.policy.autonomy = Autonomy::Autonomous;
    let out = assess(&data);
    assert_eq!(
        out.actions.first().map(|a| (a.kind, a.auto)),
        Some((ActionKind::Block, false))
    );
}

#[test]
fn assist_limits_duration_and_autonomous_escalates() {
    let mut data = input(serde_json::json!([alert(
        "brute_force",
        "critical",
        "8.8.8.8",
        9_990.0
    )]));
    data.policy.mode = Mode::Protect;
    data.strikes.insert("8.8.8.8".into(), 2);
    let assisted = assess(&data);
    assert_eq!(
        assisted.actions.first().map(|a| (a.minutes, a.auto)),
        Some((240, false))
    );
    data.policy.autonomy = Autonomy::Autonomous;
    let autonomous = assess(&data);
    assert_eq!(
        autonomous.actions.first().map(|a| (a.minutes, a.auto)),
        Some((240, true))
    );
}

#[test]
fn recon_prefers_honeypot_then_tarpit() {
    let mut data = input(serde_json::json!([alert(
        "port_scan",
        "high",
        "8.8.8.8",
        9_990.0
    )]));
    assert_eq!(
        assess(&data).actions.first().map(|a| a.kind),
        Some(ActionKind::Tarpit)
    );
    data.policy.honeypot = true;
    assert_eq!(
        assess(&data).actions.first().map(|a| a.kind),
        Some(ActionKind::Honeypot)
    );
}

#[test]
fn lan_compromise_quarantines_only_when_enabled() {
    let mut data = input(serde_json::json!([alert(
        "exfiltration",
        "critical",
        "192.168.1.77",
        9_990.0
    )]));
    assert_eq!(
        assess(&data).actions.first().map(|a| a.kind),
        Some(ActionKind::Warn)
    );
    data.policy.quarantine = true;
    assert_eq!(
        assess(&data).actions.first().map(|a| a.kind),
        Some(ActionKind::Quarantine)
    );
}

#[test]
fn budget_caps_automatic_actions() {
    let alerts: Vec<_> = (1..=5)
        .map(|n| alert("brute_force", "critical", &format!("8.8.8.{n}"), 9_990.0))
        .collect();
    let mut data = input(serde_json::Value::Array(alerts));
    data.policy.mode = Mode::Protect;
    data.policy.autonomy = Autonomy::Autonomous;
    data.policy.max_actions_per_hour = 4;
    data.recent_actions = 2;
    assert_eq!(assess(&data).actions.iter().filter(|a| a.auto).count(), 2);
}

#[test]
fn country_wave_skips_home_country() {
    let alerts: Vec<_> = (1..=3)
        .map(|n| alert("brute_force", "high", &format!("8.8.8.{n}"), 9_990.0))
        .collect();
    let mut data = input(serde_json::Value::Array(alerts));
    for n in 1..=3 {
        data.countries.insert(format!("8.8.8.{n}"), "US".into());
    }
    data.policy.country_block = true;
    data.policy.country_threshold = 3;
    let out = assess(&data);
    assert!(
        out.actions
            .iter()
            .any(|a| a.kind == ActionKind::CountryBlock && a.target == "country:US")
    );
    assert_eq!(
        out.countries
            .first()
            .map(|c| (c.country.as_str(), c.incidents)),
        Some(("US", 3))
    );
    data.policy.home_countries = vec!["us".into()];
    assert!(
        !assess(&data)
            .actions
            .iter()
            .any(|a| a.kind == ActionKind::CountryBlock)
    );
}

#[test]
fn active_targets_are_not_repeated() {
    let mut data = input(serde_json::json!([alert(
        "brute_force",
        "high",
        "8.8.8.8",
        9_990.0
    )]));
    data.active = vec!["8.8.8.8".into()];
    assert!(assess(&data).actions.is_empty());
}

#[test]
fn score_and_level_are_bounded() {
    let alerts: Vec<_> = [
        "port_scan",
        "brute_force",
        "syn_flood",
        "dns_tunnel",
        "exfiltration",
    ]
    .iter()
    .flat_map(|k| (0..10).map(move |n| alert(k, "critical", "8.8.8.8", 9_000.0 + f64::from(n))))
    .collect();
    let out = assess(&input(serde_json::Value::Array(alerts)));
    assert_eq!(
        out.incidents.first().map(|i| (i.score, i.level)),
        Some((100, Severity::Critical))
    );
}

#[test]
fn canonical_addresses_merge_and_reject_garbage() {
    assert_eq!(net::canonical("::ffff:8.8.8.8"), "8.8.8.8");
    assert_eq!(net::canonical("AA-BB-CC-DD-EE-FF"), "aa:bb:cc:dd:ee:ff");
    assert_eq!(incident::clean("bad host"), None);
    assert_eq!(incident::fingerprint("8.8.8.8").len(), 16);
    assert!(net::is_lan(
        &net::address("100.100.1.1").unwrap_or(net::Addr::V4(0))
    ));
}

#[test]
fn json_entrypoint_validates_input() {
    assert!(
        assess_json(
            "{\"now\": 1, \"alerts\": [{\"kind\": \"nope\", \"severity\": \"low\", \"at\": 1}]}"
        )
        .is_err()
    );
    assert!(assess_json("{\"now\": 1}").is_ok());
}

#[test]
fn geo_table_finds_ranges() {
    let table = GeoTable::parse(
        "1.0.0.0,1.0.0.255,AU\n8.8.8.0,8.8.8.255,US\n2001:4860::,2001:4860:ffff::,US\n9.9.9.0,9.9.9.255,ZZ\n",
    );
    let table = table.unwrap_or_default();
    assert_eq!(table.len(), 3);
    assert_eq!(table.lookup("8.8.8.8").as_deref(), Some("US"));
    assert_eq!(table.lookup("2001:4860::8888").as_deref(), Some("US"));
    assert_eq!(table.lookup("9.9.9.9"), None);
    assert_eq!(table.lookup("1.0.1.0"), None);
    assert_eq!(table.ranges("US", 10).len(), 2);
    assert_eq!(
        table.ranges("US", 1),
        vec![("8.8.8.0".to_owned(), "8.8.8.255".to_owned())]
    );
    assert!(table.ranges("ZZ", 10).is_empty());
}

#[test]
fn lan_exfiltration_sinkholes_external_destinations() {
    let mut data = input(serde_json::json!([
        {"kind": "exfiltration", "severity": "high", "src": "192.168.1.40", "dst": "203.0.113.50", "count": 9, "at": 9_990.0},
        {"kind": "dns_tunnel", "severity": "high", "src": "192.168.1.40", "dst": "192.168.1.1", "count": 9, "at": 9_991.0}
    ]));
    data.policy.mode = Mode::Protect;
    let out = assess(&data);
    let sink: Vec<_> = out
        .actions
        .iter()
        .filter(|a| a.kind == ActionKind::Sinkhole)
        .collect();
    assert_eq!(sink.len(), 1);
    assert_eq!(
        sink.first().map(|a| (a.target.as_str(), a.auto)),
        Some(("203.0.113.50", true))
    );
}

#[test]
fn geo_table_rejects_overlaps_and_garbage() {
    assert!(GeoTable::parse("1.0.0.0,1.0.0.255,AU\n1.0.0.10,1.0.1.0,US\n").is_err());
    assert!(GeoTable::parse("hello\nworld\n").is_err());
    assert!(GeoTable::parse("").is_err());
}
