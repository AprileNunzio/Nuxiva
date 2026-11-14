use super::*;
use crate::{Mode, Reason};

fn codes(reasons: &[Reason]) -> Vec<&'static str> {
    reasons.iter().map(|r| r.code).collect()
}

#[test]
fn meeting_signal_becomes_widget_proposal_with_valid_task_and_explanation() {
    let mut e = engine();
    let now = DAY + 12 * HOUR;
    let out = e
        .ingest(
            &sig(
                "calendar",
                "event_in_minutes",
                Some("anna"),
                "standup",
                10,
                now,
            ),
            &idle(&["anna"]),
            now,
        )
        .expect("ingest");
    assert_eq!(out.len(), 1);
    let d = &out[0];
    assert_eq!(d.mode, Mode::Widget);
    assert_eq!(d.confidence, 800);
    let task = d.action.as_ref().expect("task");
    assert_eq!(task.input_ref, "event:standup");
    assert!(task.validate().is_ok());
    assert!(codes(&d.explanation.reasons).contains(&"proactive.why.signal"));
    assert_eq!(e.explain(d.id).expect("why").origin, "signal");
    assert_eq!(e.pending().len(), 1);
}

#[test]
fn speaks_only_when_voice_is_free_and_idle() {
    let mut e = engine();
    let now = DAY + 12 * HOUR;
    let c = ctx(Situation::Idle, &["anna"], false, true);
    let out = e
        .ingest(
            &sig("calendar", "event_in_minutes", Some("anna"), "a", 5, now),
            &c,
            now,
        )
        .expect("ingest");
    assert_eq!(out[0].mode, Mode::Speak);
}

#[test]
fn low_confidence_goes_to_the_diary_with_the_reason() {
    let mut e = engine();
    let now = DAY + 12 * HOUR;
    let out = e
        .ingest(&sig("home", "hint", None, "x", 1, now), &idle(&[]), now)
        .expect("ingest");
    assert_eq!(out[0].mode, Mode::Diary);
    assert!(!out[0].deferred);
    assert!(codes(&out[0].explanation.reasons).contains(&"proactive.why.low_confidence"));
    assert!(e.pending().is_empty());
    assert_eq!(e.stats().silent, 1);
}

#[test]
fn duplicates_are_suppressed() {
    let mut e = engine();
    let now = DAY + 12 * HOUR;
    let s = sig(
        "calendar",
        "event_in_minutes",
        Some("anna"),
        "standup",
        10,
        now,
    );
    assert_eq!(e.ingest(&s, &idle(&["anna"]), now).expect("a").len(), 1);
    assert!(
        e.ingest(&s, &idle(&["anna"]), now + 1_000)
            .expect("b")
            .is_empty()
    );
}

#[test]
fn conversation_defers_and_tick_resurfaces_when_idle() {
    let mut e = engine();
    let now = DAY + 12 * HOUR;
    let busy = ctx(Situation::Conversation, &["anna"], false, true);
    let out = e
        .ingest(
            &sig(
                "calendar",
                "event_in_minutes",
                Some("anna"),
                "standup",
                10,
                now,
            ),
            &busy,
            now,
        )
        .expect("ingest");
    assert_eq!(out[0].mode, Mode::Diary);
    assert!(out[0].deferred);
    assert!(e.pending().is_empty());
    assert!(e.tick(&busy, now + MIN).expect("tick").is_empty());
    let back = e.tick(&idle(&["anna"]), now + 2 * MIN).expect("tick");
    assert_eq!(back.len(), 1);
    assert_eq!(back[0].mode, Mode::Widget);
    assert!(
        e.tick(&idle(&["anna"]), now + 3 * MIN)
            .expect("tick")
            .is_empty()
    );
}

#[test]
fn hourly_cap_defers_the_extra_interruptions() {
    let mut e = engine();
    let now = DAY + 12 * HOUR;
    let mut surfaced = 0;
    let mut deferred = 0;
    for i in 0..8_u64 {
        let who = format!("p{i}");
        let s = sig(
            "calendar",
            "event_in_minutes",
            Some(&who),
            &format!("e{i}"),
            5,
            now + i,
        );
        for d in e.ingest(&s, &idle(&[]), now + i).expect("ingest") {
            if d.mode == Mode::Diary && d.deferred {
                deferred += 1;
            } else {
                surfaced += 1;
            }
        }
    }
    assert_eq!(surfaced, 6);
    assert_eq!(deferred, 2);
    assert_eq!(e.stats().capped, 2);
}

#[test]
fn person_cap_limits_a_single_person() {
    let mut e = engine();
    let now = DAY + 12 * HOUR;
    let mut shown = 0;
    for i in 0..6_u64 {
        let s = sig(
            "calendar",
            "event_in_minutes",
            Some("anna"),
            &format!("e{i}"),
            5,
            now + i,
        );
        shown += e
            .ingest(&s, &idle(&["anna"]), now + i)
            .expect("ingest")
            .iter()
            .filter(|d| d.mode != Mode::Diary)
            .count();
    }
    assert_eq!(shown, 4);
}

#[test]
fn critical_bypasses_caps_cost_and_quiet_hours() {
    let mut e = engine();
    let night = DAY + 2 * HOUR;
    let busy = ctx(Situation::Conversation, &[], false, true);
    let out = e
        .ingest(
            &sig("security", "intrusion", None, "garage", 1, night),
            &busy,
            night,
        )
        .expect("ingest");
    assert_eq!(out[0].mode, Mode::Speak);
    assert!(out[0].action.is_some());
    assert_eq!(out[0].score, 950 * 1000 / 1000);
}

#[test]
fn quiet_hours_defer_normal_rules() {
    let mut e = engine();
    let night = DAY + 23 * HOUR;
    let out = e
        .ingest(
            &sig(
                "calendar",
                "event_in_minutes",
                Some("anna"),
                "late",
                5,
                night,
            ),
            &idle(&["anna"]),
            night,
        )
        .expect("ingest");
    assert!(out[0].deferred);
    assert!(codes(&out[0].explanation.reasons).contains(&"proactive.why.quiet_hours"));
    let morning = DAY + 24 * HOUR + 8 * HOUR;
    assert_eq!(e.tick(&idle(&["anna"]), morning).expect("tick").len(), 0);
}

#[test]
fn pending_expires_and_accepting_late_fails() {
    let mut e = engine();
    let now = DAY + 12 * HOUR;
    let out = e
        .ingest(
            &sig("calendar", "event_in_minutes", Some("anna"), "a", 5, now),
            &idle(&["anna"]),
            now,
        )
        .expect("ingest");
    let id = out[0].id;
    assert!(
        e.tick(&idle(&["anna"]), now + 2 * HOUR)
            .expect("tick")
            .is_empty()
    );
    assert!(e.pending().is_empty());
    assert_eq!(e.stats().expired, 1);
    assert!(e.accept(id, now + 2 * HOUR).is_err());
}

#[test]
fn accept_returns_the_task_once() {
    let mut e = engine();
    let now = DAY + 12 * HOUR;
    let id = e
        .ingest(
            &sig("calendar", "event_in_minutes", Some("anna"), "a", 5, now),
            &idle(&["anna"]),
            now,
        )
        .expect("ingest")[0]
        .id;
    assert_eq!(
        e.accept(id, now + 1).expect("task").kind,
        "calendar.prepare"
    );
    assert!(e.accept(id, now + 2).is_err());
    assert_eq!(e.acceptance_permille(), Some(1_000));
}

#[test]
fn notify_level_is_informational_only() {
    let mut e = engine();
    let now = DAY + 12 * HOUR;
    let c = idle(&[]);
    e.ingest(&sig("presence", "home", None, "", 0, now), &c, now)
        .expect("fact");
    let out = e
        .ingest(
            &sig("home", "window_open", None, "kitchen", 1, now + 1),
            &c,
            now + 1,
        )
        .expect("ingest");
    assert_eq!(out[0].mode, Mode::Widget);
    assert!(out[0].action.is_none());
    assert!(e.accept(out[0].id, now + 2).is_err());
    assert!(e.dismiss(out[0].id).is_ok());
}

#[test]
fn conditions_gate_the_rule() {
    let mut e = engine();
    let now = DAY + 18 * HOUR;
    let c = idle(&["anna"]);
    let dusk = |at| sig("home", "dusk", Some("anna"), "salotto", 1, at);
    assert!(e.ingest(&dusk(now), &c, now).expect("no fact").is_empty());
    e.ingest(&sig("presence", "home", Some("anna"), "", 1, now), &c, now)
        .expect("fact");
    let out = e.ingest(&dusk(now + 1), &c, now + 1).expect("with fact");
    assert_eq!(out.len(), 1);
    let early = DAY + 3 * HOUR;
    assert!(
        e.ingest(&dusk(early), &c, early)
            .expect("window")
            .is_empty()
    );
}
