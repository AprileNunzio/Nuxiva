use super::*;
use crate::{Mode, Reason};

fn has(reasons: &[Reason], code: &str) -> bool {
    reasons.iter().any(|r| r.code == code)
}

fn lights(e: &mut Engine, at: u64, room: &str) -> Vec<crate::Decision> {
    let c = idle(&["anna"]);
    e.ingest(&sig("presence", "home", Some("anna"), "", 1, at), &c, at)
        .expect("fact");
    e.ingest(
        &sig("home", "dusk", Some("anna"), room, 1, at + 1),
        &c,
        at + 1,
    )
    .expect("dusk")
}

#[test]
fn do_and_tell_needs_approval_then_executes_with_undo() {
    let mut e = engine();
    let t = DAY + 18 * HOUR;
    let first = lights(&mut e, t, "salotto");
    assert_eq!(first[0].mode, Mode::Widget);
    assert!(has(
        &first[0].explanation.reasons,
        "proactive.why.needs_approval"
    ));
    e.approve_always("lights").expect("approve");
    let second = lights(&mut e, t + HOUR, "cucina");
    assert_eq!(second[0].mode, Mode::Execute);
    assert!(second[0].undoable);
    assert!(has(
        &second[0].explanation.reasons,
        "proactive.why.auto_approved"
    ));
    assert_eq!(e.undoable(), vec![second[0].id]);
    let undo = e.undo(second[0].id, t + HOUR + MIN).expect("undo");
    assert_eq!(undo.kind, "lights.off");
    assert_eq!(undo.input_ref, "room:cucina");
    assert!(e.undo(second[0].id, t + HOUR + 2 * MIN).is_err());
    assert_eq!(e.stats().undone, 1);
}

#[test]
fn undo_window_expires() {
    let mut e = engine();
    let t = DAY + 18 * HOUR;
    e.approve_always("lights").expect("approve");
    let d = lights(&mut e, t, "salotto");
    assert_eq!(d[0].mode, Mode::Execute);
    assert!(e.undo(d[0].id, t + 11 * MIN).is_err());
}

#[test]
fn repeated_undo_demotes_the_level_back_to_a_proposal() {
    let mut e = engine();
    let mut t = DAY + 18 * HOUR;
    e.approve_always("lights").expect("approve");
    for room in ["a", "b"] {
        let d = lights(&mut e, t, room);
        assert_eq!(d[0].mode, Mode::Execute);
        e.undo(d[0].id, t + 1).expect("undo");
        t += 20 * MIN;
    }
    let next = lights(&mut e, t, "c");
    assert_eq!(next[0].mode, Mode::Widget);
    assert!(has(
        &next[0].explanation.reasons,
        "proactive.why.level_lowered"
    ));
}

#[test]
fn approving_always_requires_a_reversible_low_risk_rule() {
    let mut e = engine();
    assert!(e.approve_always("mail_important").is_err());
    assert!(e.approve_always("meeting_soon").is_err());
    assert!(e.approve_always("nope").is_err());
    assert!(e.approve_always("lights").is_ok());
}

#[test]
fn acceptances_raise_and_refusals_lower_confidence() {
    let mut up = engine();
    let mut down = engine();
    let mut t = DAY + 8 * HOUR;
    for i in 0..4 {
        let s = |n: u64| {
            sig(
                "calendar",
                "event_in_minutes",
                Some("anna"),
                &format!("e{n}"),
                5,
                t + n,
            )
        };
        let a = up.ingest(&s(i), &idle(&["anna"]), t).expect("up");
        up.accept(a[0].id, t + 1).expect("accept");
        let b = down.ingest(&s(i), &idle(&["anna"]), t).expect("down");
        down.refuse(b[0].id, t + 1).expect("refuse");
        t += 2 * HOUR;
    }
    let probe = |e: &mut Engine, at: u64| {
        e.ingest(
            &sig("calendar", "event_in_minutes", Some("anna"), "probe", 5, at),
            &idle(&["anna"]),
            at,
        )
        .expect("probe")
    };
    let hi = probe(&mut up, t);
    let lo = probe(&mut down, t);
    assert!(hi[0].confidence > 800);
    assert!(lo[0].confidence < 800);
    assert!(has(&hi[0].explanation.reasons, "proactive.why.learned_up"));
    assert!(has(
        &lo[0].explanation.reasons,
        "proactive.why.learned_down"
    ));
}

#[test]
fn many_refusals_mute_the_rule_until_reset() {
    let mut e = engine();
    let mut t = DAY + 8 * HOUR;
    for i in 0..8_u64 {
        let out = e
            .ingest(
                &sig(
                    "calendar",
                    "event_in_minutes",
                    Some("anna"),
                    &format!("e{i}"),
                    5,
                    t,
                ),
                &idle(&["anna"]),
                t,
            )
            .expect("ingest");
        if let Some(d) = out.first().filter(|d| d.mode != Mode::Diary) {
            e.refuse(d.id, t + 1).expect("refuse");
        }
        t += HOUR;
    }
    let muted = e
        .ingest(
            &sig("calendar", "event_in_minutes", Some("anna"), "late", 5, t),
            &idle(&["anna"]),
            t,
        )
        .expect("muted");
    assert_eq!(muted[0].mode, Mode::Diary);
    assert!(
        has(
            &muted[0].explanation.reasons,
            "proactive.why.muted_by_feedback"
        ) || has(
            &muted[0].explanation.reasons,
            "proactive.why.low_confidence"
        )
    );
    e.reset_learning("meeting_soon", Some("anna"));
    let again = e
        .ingest(
            &sig(
                "calendar",
                "event_in_minutes",
                Some("anna"),
                "later",
                5,
                t + HOUR,
            ),
            &idle(&["anna"]),
            t + HOUR,
        )
        .expect("again");
    assert_ne!(again[0].mode, Mode::Diary);
}

#[test]
fn learning_is_per_person() {
    let mut e = engine();
    let t = DAY + 8 * HOUR;
    for i in 0..6_u64 {
        let at = t + i * 2 * HOUR;
        let out = e
            .ingest(
                &sig(
                    "calendar",
                    "event_in_minutes",
                    Some("anna"),
                    &format!("e{i}"),
                    5,
                    at,
                ),
                &idle(&["anna"]),
                at,
            )
            .expect("ingest");
        if let Some(d) = out.first().filter(|d| d.mode != Mode::Diary) {
            e.refuse(d.id, at + 1).expect("refuse");
        }
    }
    let at = t + 14 * HOUR;
    let other = e
        .ingest(
            &sig("calendar", "event_in_minutes", Some("luca"), "x", 5, at),
            &idle(&["luca"]),
            at,
        )
        .expect("other");
    assert_eq!(other[0].confidence, 800);
}

#[test]
fn state_roundtrip_keeps_learning_approval_and_policies() {
    let mut e = engine();
    e.approve_always("lights").expect("approve");
    let t = DAY + 8 * HOUR;
    let out = e
        .ingest(
            &sig("calendar", "event_in_minutes", Some("anna"), "a", 5, t),
            &idle(&["anna"]),
            t,
        )
        .expect("ingest");
    e.refuse(out[0].id, t + 1).expect("refuse");
    let saved = e.export_state().expect("export");
    let mut fresh = engine();
    fresh.import_state(&saved).expect("import");
    assert_eq!(fresh.export_state().expect("again"), saved);
    let l = lights(&mut fresh, DAY + 18 * HOUR, "salotto");
    assert_eq!(l[0].mode, Mode::Execute);
}

#[test]
fn hostile_state_is_rejected() {
    let mut e = engine();
    let bad = r#"{"learner":{},"habits":{},"policies":{},"approved":["mail_important"]}"#;
    assert!(e.import_state(bad).is_err());
    assert!(e.import_state("{").is_err());
    assert!(e.import_state(r#"{"learner":{},"habits":{"ghost|":{"hits":[],"stamp":[],"days":[],"last_day":0}},"policies":{},"approved":[]}"#).is_err());
    let huge = "x".repeat(crate::MAX_PAYLOAD + 1);
    assert!(e.import_state(&huge).is_err());
}

#[test]
fn old_feedback_fades_so_a_silenced_rule_can_recover() {
    let mut e = engine();
    let mut t = DAY + 8 * HOUR;
    for i in 0..6_u64 {
        let out = e
            .ingest(
                &sig(
                    "calendar",
                    "event_in_minutes",
                    Some("anna"),
                    &format!("e{i}"),
                    5,
                    t,
                ),
                &idle(&["anna"]),
                t,
            )
            .expect("ingest");
        if let Some(d) = out.first().filter(|d| d.mode != Mode::Diary) {
            e.refuse(d.id, t + 1).expect("refuse");
        }
        t += HOUR;
    }
    let later = t + 120 * 86_400_000;
    let out = e
        .ingest(
            &sig(
                "calendar",
                "event_in_minutes",
                Some("anna"),
                "again",
                5,
                later,
            ),
            &idle(&["anna"]),
            later,
        )
        .expect("later");
    assert_eq!(out[0].mode, Mode::Widget);
    assert_eq!(out[0].confidence, 800);
}
