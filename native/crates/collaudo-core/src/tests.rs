use std::collections::BTreeMap;
use std::path::PathBuf;

use crate::*;

fn dir(tag: &str) -> PathBuf {
    let id = random_id().unwrap_or_default();
    let path = std::env::temp_dir().join(format!("collaudo-{tag}-{id}"));
    let _ = std::fs::remove_dir_all(&path);
    path
}

fn hub(tag: &str, segment: u64, keep: usize) -> (Hub, PathBuf) {
    let path = dir(tag);
    let cfg = StoreConfig {
        dir: path.clone(),
        segment_bytes: segment,
        keep_segments: keep,
        key: [7; 32],
    };
    (Hub::open(cfg).unwrap_or_else(|_| unreachable!()), path)
}

fn raw(domain: Domain, level: Level, kind: &str, fields: &[(&str, Scalar)]) -> RawEvent {
    RawEvent {
        domain,
        level,
        kind: kind.to_owned(),
        corr: Some("abcdef0123456789".to_owned()),
        src: "test".to_owned(),
        fields: fields
            .iter()
            .map(|(k, v)| ((*k).to_owned(), v.clone()))
            .collect(),
        at_ms: Some(1_700_000_000_000),
    }
}

fn text(v: &str) -> Scalar {
    Scalar::Text(v.to_owned())
}

#[test]
fn redacts_personal_data() {
    let (hub, _) = hub("redact", 1 << 20, 4);
    let fields = [
        ("speaker_name", text("Mario Rossi")),
        ("transcript", text("ho allergia alle noci")),
        ("contact", text("mario.rossi@example.com")),
        ("phone_note", text("3331234567")),
        ("zone", text("kitchen")),
        ("frames", Scalar::Int(3)),
    ];
    assert!(matches!(
        hub.emit(raw(Domain::Ear, Level::Info, "verdict", &fields)),
        Ok(Some(1))
    ));
    let events = hub.query(&Query::default()).unwrap_or_default();
    let line = serde_json::to_string(&events).unwrap_or_default();
    for leak in ["Mario", "Rossi", "noci", "example.com", "3331234567"] {
        assert!(!line.contains(leak), "{leak}");
    }
    let first = events.first().map(|e| e.fields.clone()).unwrap_or_default();
    assert_eq!(first.get("zone"), Some(&text("kitchen")));
    assert_eq!(first.get("frames"), Some(&Scalar::Int(3)));
    assert!(first.contains_key("redacted_n"));
    let fields = [("spk_ref", text("mario")), ("zone", text("hall"))];
    assert!(
        hub.emit(raw(Domain::Ear, Level::Info, "heard", &fields))
            .is_ok()
    );
    let again = hub
        .query(&Query {
            since_seq: 1,
            ..Query::default()
        })
        .unwrap_or_default();
    let spk = again.first().and_then(|e| e.fields.get("spk_ref")).cloned();
    assert!(matches!(spk, Some(Scalar::Text(t)) if t.starts_with("h:") && !t.contains("mario")));
}

#[test]
fn scrubs_error_messages_but_keeps_context() {
    let scrubbed =
        Redactor::scrub_text("failed for /home/mario/docs mail a.b@c.it id 12345678901 ok");
    assert!(scrubbed.contains("failed for /home/~"));
    assert!(!scrubbed.contains("mario"));
    assert!(!scrubbed.contains("a.b@c.it"));
    assert!(!scrubbed.contains("12345678901"));
    assert!(scrubbed.contains("ok"));
}

#[test]
fn anonymous_ids_are_stable_and_scoped() {
    let r = Redactor::new([1; 32]);
    assert_eq!(r.anon("person", "mario"), r.anon("person", "mario"));
    assert_ne!(r.anon("person", "mario"), r.anon("guest", "mario"));
    assert!(!r.anon("person", "mario").contains("mario"));
}

#[test]
fn verbose_only_in_collaudo_mode() {
    let (hub, _) = hub("mode", 1 << 20, 4);
    assert!(matches!(
        hub.emit(raw(Domain::Vision, Level::Trace, "frame", &[])),
        Ok(None)
    ));
    assert!(hub.set_mode(Mode::Collaudo).is_ok());
    assert!(matches!(
        hub.emit(raw(Domain::Vision, Level::Trace, "frame", &[])),
        Ok(Some(_))
    ));
    assert_eq!(hub.stats().map_or(0, |s| s.dropped_verbose), 1);
}

#[test]
fn rotation_retention_and_chain() {
    let (hub, path) = hub("rotate", 1500, 3);
    for _ in 0..60 {
        assert!(
            hub.emit(raw(
                Domain::Supervisor,
                Level::Info,
                "tick",
                &[("n", Scalar::Int(1))]
            ))
            .is_ok()
        );
    }
    assert!(hub.flush().is_ok());
    let segs = std::fs::read_dir(&path).map_or(0, |d| {
        d.filter_map(Result::ok)
            .filter(|e| e.path().extension().is_some_and(|x| x == "jsonl"))
            .count()
    });
    assert_eq!(segs, 3);
    let integrity = hub.verify().unwrap_or_else(|_| unreachable!());
    assert!(integrity.ok);
    drop(hub);
    let cfg = StoreConfig {
        dir: path,
        segment_bytes: 1500,
        keep_segments: 3,
        key: [7; 32],
    };
    let reopened = Hub::open(cfg).unwrap_or_else(|_| unreachable!());
    assert!(reopened.verify().is_ok_and(|i| i.ok));
    let next = reopened.emit(raw(Domain::Supervisor, Level::Info, "tick", &[]));
    assert!(matches!(next, Ok(Some(61))));
}

#[test]
fn tampering_is_detected() {
    let (hub, path) = hub("tamper", 1 << 20, 4);
    for i in 0..5 {
        assert!(
            hub.emit(raw(
                Domain::Mcp,
                Level::Info,
                "call",
                &[("n", Scalar::Int(i))]
            ))
            .is_ok()
        );
    }
    let file = std::fs::read_dir(&path).ok().and_then(|d| {
        d.filter_map(Result::ok)
            .map(|e| e.path())
            .find(|p| p.extension().is_some_and(|x| x == "jsonl"))
    });
    let file = file.unwrap_or_else(|| unreachable!());
    let body = std::fs::read_to_string(&file)
        .unwrap_or_default()
        .replacen("\"n\":2", "\"n\":9", 1);
    assert!(std::fs::write(&file, body).is_ok());
    assert!(!hub.verify().is_ok_and(|i| i.ok));
}

#[test]
fn query_filters_and_cursor() {
    let (hub, _) = hub("query", 1 << 20, 4);
    assert!(
        hub.emit(raw(Domain::Ear, Level::Info, "verdict", &[]))
            .is_ok()
    );
    assert!(
        hub.emit(raw(
            Domain::Error,
            Level::Error,
            "unhandled",
            &[("msg", text("boom"))]
        ))
        .is_ok()
    );
    assert!(
        hub.emit(raw(Domain::Vision, Level::Warn, "slow", &[]))
            .is_ok()
    );
    let q = Query {
        min_level: Some(Level::Warn),
        ..Query::default()
    };
    assert_eq!(hub.query(&q).map_or(0, |v| v.len()), 2);
    let q = Query {
        since_seq: 2,
        ..Query::default()
    };
    assert_eq!(hub.query(&q).map_or(0, |v| v.len()), 1);
    let q = Query {
        corr: Some("abcdef0123456789".to_owned()),
        domain: Some(Domain::Error),
        ..Query::default()
    };
    assert_eq!(hub.query(&q).map_or(0, |v| v.len()), 1);
}

#[test]
fn rejects_invalid_events() {
    let (hub, _) = hub("invalid", 1 << 20, 4);
    let mut bad = raw(Domain::Ear, Level::Info, "Bad Kind!", &[]);
    assert!(hub.emit(bad.clone()).is_err());
    bad.kind = "ok".to_owned();
    bad.corr = Some("zz".to_owned());
    assert!(hub.emit(bad).is_err());
    assert!(hub.emit_json("{\"domain\":\"ear\",\"extra\":1}").is_err());
    assert!(hub.emit_json(&"x".repeat(20_000)).is_err());
}

#[test]
fn token_vault_issues_and_verifies() {
    let path = dir("token").join("t");
    let vault = TokenVault::at(&path);
    let token = vault.issue().unwrap_or_default();
    assert_eq!(token.len(), 64);
    assert!(vault.verify(&token));
    assert!(!vault.verify(&"0".repeat(64)));
    assert!(!vault.verify("short"));
    let stored = std::fs::read_to_string(&path).unwrap_or_default();
    assert!(!stored.contains(&token));
    assert!(vault.revoke().is_ok());
    assert!(!vault.verify(&token));
}

fn probe_event(seq: u64, kind: &str, fields: &[(&str, Scalar)]) -> Envelope {
    Envelope {
        v: SCHEMA,
        seq,
        id: "0123456789abcdef".to_owned(),
        at_ms: 1_700_000_000_000_u64.saturating_add(seq),
        domain: Domain::Probe,
        level: Level::Info,
        kind: kind.to_owned(),
        corr: None,
        src: "smoke".to_owned(),
        fields: fields
            .iter()
            .map(|(k, v)| ((*k).to_owned(), v.clone()))
            .collect::<BTreeMap<_, _>>(),
    }
}

#[test]
fn smoke_spec_judges_latency_and_missing() {
    let ok = text("ok");
    let events = vec![
        probe_event(
            1,
            "voice_first_audio",
            &[("outcome", ok.clone()), ("latency_ms", Scalar::Int(1200))],
        ),
        probe_event(
            2,
            "bus_roundtrip",
            &[("outcome", ok.clone()), ("latency_ms", Scalar::Float(4.2))],
        ),
        probe_event(3, "camera_frame", &[("outcome", text("skip"))]),
    ];
    let report = analyze(&events, &default_spec());
    let find = |id: &str| report.checks.iter().find(|c| c.id == id).map(|c| c.status);
    assert_eq!(find("voice_first_audio"), Some(Status::Fail));
    assert_eq!(find("bus_roundtrip"), Some(Status::Pass));
    assert_eq!(find("camera_frame"), Some(Status::Skip));
    assert_eq!(find("barge_in"), Some(Status::Missing));
    assert_eq!(report.verdict, Verdict::Fail);
    assert_eq!(
        report.latency.get("probe.voice_first_audio").map(|l| l.max),
        Some(1200.0)
    );
}

#[test]
fn regressions_are_found() {
    let ok = text("ok");
    let good = analyze(
        &[probe_event(
            1,
            "bus_roundtrip",
            &[("outcome", ok.clone()), ("latency_ms", Scalar::Int(10))],
        )],
        &default_spec(),
    );
    let bad = analyze(
        &[probe_event(
            2,
            "bus_roundtrip",
            &[("outcome", ok), ("latency_ms", Scalar::Int(900))],
        )],
        &default_spec(),
    );
    let regressions = compare(&good, &bad);
    assert!(
        regressions
            .iter()
            .any(|r| r.subject == "bus_roundtrip" && r.kind == "check")
    );
    assert_eq!(analyze(&[], &default_spec()).verdict, Verdict::Insufficient);
}
