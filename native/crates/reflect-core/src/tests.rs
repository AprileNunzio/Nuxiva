use crate::*;

pub(crate) const DAY: u64 = 86_400_000;

pub(crate) fn catalog() -> Catalog {
    Catalog::from_json(
        r#"{"kinds":{"reminder_time":{"domain":"habits","max_value_len":16,"allowed_values":["morning","evening"]},
        "tone":{"domain":"voice","max_value_len":16},"step_order":{"domain":"build","max_value_len":32}}}"#,
    )
    .expect("catalog")
}

pub(crate) fn store() -> Store {
    Store::new(Settings::default(), catalog()).expect("store")
}

pub(crate) fn refl(
    task: &str,
    outcome: Outcome,
    attempts: u32,
    observed: &[(&str, &str)],
    proposed: Option<Delta>,
) -> Reflection {
    Reflection {
        schema_version: SCHEMA_VERSION,
        task: task.into(),
        outcome,
        signals: Signals {
            duration_ms: 10,
            attempts,
            user_corrections: 0,
            user_rejections: 0,
        },
        observed: observed
            .iter()
            .map(|(k, v)| Observed {
                kind: (*k).into(),
                value: (*v).into(),
            })
            .collect(),
        proposed,
    }
}

#[allow(clippy::unnecessary_wraps)]
pub(crate) fn cand(kind: &str, value: &str) -> Option<Delta> {
    Some(Delta::Data {
        candidate: Candidate {
            kind: kind.into(),
            value: value.into(),
        },
    })
}

fn feed(s: &mut Store, good: usize, bad: usize, now: u64) {
    for i in 0..good {
        s.record(
            &refl(
                &format!("g{i}"),
                Outcome::Success,
                1,
                &[("reminder_time", "evening")],
                None,
            ),
            now,
        )
        .expect("good");
    }
    for i in 0..bad {
        s.record(
            &refl(
                &format!("b{i}"),
                Outcome::Failure,
                2,
                &[("reminder_time", "morning")],
                None,
            ),
            now,
        )
        .expect("bad");
    }
}

#[test]
fn score_uses_outcome_and_signals() {
    let s = Settings::default();
    assert_eq!(refl("a", Outcome::Success, 1, &[], None).score(&s), 1_000);
    assert_eq!(refl("a", Outcome::Success, 3, &[], None).score(&s), 800);
    assert_eq!(refl("a", Outcome::Failure, 1, &[], None).score(&s), 0);
    assert_eq!(refl("a", Outcome::Cancelled, 1, &[], None).score(&s), 300);
    let mut r = refl("a", Outcome::Success, 1, &[], None);
    r.signals.user_rejections = 9;
    assert_eq!(r.score(&s), 0);
}

#[test]
fn lesson_is_adopted_only_after_verification() {
    let mut s = store();
    feed(&mut s, 3, 4, 0);
    let out = s
        .record(
            &refl(
                "c",
                Outcome::Success,
                1,
                &[("reminder_time", "evening")],
                cand("reminder_time", "evening"),
            ),
            0,
        )
        .expect("record");
    assert!(out.adopted.is_empty());
    assert_eq!(s.lessons(LessonState::Candidate).len(), 1);
    feed(&mut s, 2, 0, 1);
    let adopted = s.lesson_for("reminder_time").expect("adopted");
    assert_eq!(adopted.value, "evening");
    assert_eq!(adopted.version, 1);
}

#[test]
fn lesson_that_does_not_help_is_never_adopted() {
    let mut s = store();
    for i in 0..10 {
        s.record(
            &refl(
                &format!("m{i}"),
                Outcome::Success,
                1,
                &[("reminder_time", "morning")],
                None,
            ),
            0,
        )
        .expect("m");
    }
    for i in 0..10 {
        s.record(
            &refl(
                &format!("e{i}"),
                Outcome::Failure,
                1,
                &[("reminder_time", "evening")],
                cand("reminder_time", "evening"),
            ),
            0,
        )
        .expect("e");
    }
    assert!(s.lesson_for("reminder_time").is_none());
}

#[test]
fn needs_contrast_and_enough_samples() {
    let mut s = store();
    for i in 0..10 {
        s.record(
            &refl(
                &format!("e{i}"),
                Outcome::Success,
                1,
                &[("reminder_time", "evening")],
                cand("reminder_time", "evening"),
            ),
            0,
        )
        .expect("e");
    }
    assert!(s.lesson_for("reminder_time").is_none());
}

#[test]
fn unknown_kinds_and_bad_values_are_refused() {
    let mut s = store();
    assert_eq!(
        s.record(&refl("a", Outcome::Success, 1, &[("nope", "x")], None), 0)
            .err(),
        Some(ReflectError::UnknownKind)
    );
    assert_eq!(
        s.record(
            &refl(
                "a",
                Outcome::Success,
                1,
                &[("reminder_time", "midnight")],
                None
            ),
            0
        )
        .err(),
        Some(ReflectError::BadValue)
    );
    assert_eq!(
        s.record(
            &refl("a", Outcome::Success, 1, &[], cand("tone", "a\u{0}b")),
            0
        )
        .err(),
        Some(ReflectError::BadValue)
    );
    assert_eq!(
        s.record(&refl("Bad Task", Outcome::Success, 1, &[], None), 0)
            .err(),
        Some(ReflectError::Invalid)
    );
    let mut wrong = refl("a", Outcome::Success, 1, &[], None);
    wrong.schema_version = 9;
    assert_eq!(s.record(&wrong, 0).err(), Some(ReflectError::Version));
    assert_eq!(s.history_len(), 0);
}

#[test]
fn repeated_proposals_add_evidence_not_duplicates() {
    let mut s = store();
    for i in 0..3 {
        s.record(
            &refl(
                &format!("t{i}"),
                Outcome::Success,
                1,
                &[],
                cand("tone", "warm"),
            ),
            0,
        )
        .expect("t");
    }
    let c = s.lessons(LessonState::Candidate);
    assert_eq!(c.len(), 1);
    assert_eq!(c[0].evidence, 3);
}

#[test]
fn user_can_confirm_a_candidate_and_it_survives_regression() {
    let mut s = store();
    let out = s
        .record(
            &refl("t", Outcome::Success, 1, &[], cand("tone", "warm")),
            0,
        )
        .expect("t");
    let id = out.candidate.expect("id");
    s.confirm(id, 5).expect("confirm");
    assert_eq!(s.lesson_for("tone").expect("tone").value, "warm");
    for i in 0..30 {
        s.record(
            &refl(
                &format!("w{i}"),
                Outcome::Failure,
                1,
                &[("tone", "warm")],
                None,
            ),
            6,
        )
        .expect("w");
        s.record(
            &refl(
                &format!("c{i}"),
                Outcome::Success,
                1,
                &[("tone", "cool")],
                None,
            ),
            6,
        )
        .expect("c");
    }
    assert!(s.lesson_for("tone").is_some());
}

#[test]
fn unconfirmed_lesson_that_starts_hurting_is_withdrawn() {
    let mut s = store();
    feed(&mut s, 5, 5, 0);
    s.record(
        &refl(
            "c",
            Outcome::Success,
            1,
            &[("reminder_time", "evening")],
            cand("reminder_time", "evening"),
        ),
        0,
    )
    .expect("c");
    assert!(s.lesson_for("reminder_time").is_some());
    for i in 0..40 {
        s.record(
            &refl(
                &format!("bad{i}"),
                Outcome::Failure,
                3,
                &[("reminder_time", "evening")],
                None,
            ),
            1,
        )
        .expect("bad");
        s.record(
            &refl(
                &format!("ok{i}"),
                Outcome::Success,
                1,
                &[("reminder_time", "morning")],
                None,
            ),
            1,
        )
        .expect("ok");
    }
    assert!(s.lesson_for("reminder_time").is_none());
}

#[test]
fn newer_version_replaces_and_revert_restores_previous() {
    let mut s = store();
    let a = s
        .record(
            &refl("a", Outcome::Success, 1, &[], cand("tone", "warm")),
            0,
        )
        .expect("a")
        .candidate
        .expect("id");
    s.confirm(a, 1).expect("a");
    let b = s
        .record(
            &refl("b", Outcome::Success, 1, &[], cand("tone", "cool")),
            2,
        )
        .expect("b")
        .candidate
        .expect("id");
    s.confirm(b, 3).expect("b");
    assert_eq!(s.lesson_for("tone").expect("tone").value, "cool");
    s.revert("tone", 4).expect("revert");
    assert_eq!(s.lesson_for("tone").expect("tone").value, "warm");
    s.revert("tone", 5).expect("revert again");
    assert!(s.lesson_for("tone").is_none());
    assert_eq!(s.revert("tone", 6), Err(ReflectError::NotFound));
}

#[test]
fn rejection_forgets_and_blocks_for_a_while() {
    let mut s = store();
    let id = s
        .record(
            &refl("a", Outcome::Success, 1, &[], cand("tone", "warm")),
            0,
        )
        .expect("a")
        .candidate
        .expect("id");
    s.confirm(id, 1).expect("confirm");
    s.reject(id, 2).expect("reject");
    assert!(s.lesson_for("tone").is_none());
    assert_eq!(s.reject(id, 3), Err(ReflectError::State));
    let again = s
        .record(
            &refl("b", Outcome::Success, 1, &[], cand("tone", "warm")),
            4,
        )
        .expect("b");
    assert!(again.blocked && again.candidate.is_none());
    let later = s
        .record(
            &refl("c", Outcome::Success, 1, &[], cand("tone", "warm")),
            2 + 31 * DAY,
        )
        .expect("c");
    assert!(later.candidate.is_some());
}

#[test]
fn rejecting_adopted_restores_the_previous_one() {
    let mut s = store();
    let a = s
        .record(
            &refl("a", Outcome::Success, 1, &[], cand("tone", "warm")),
            0,
        )
        .expect("a")
        .candidate
        .expect("id");
    s.confirm(a, 1).expect("a");
    let b = s
        .record(
            &refl("b", Outcome::Success, 1, &[], cand("tone", "cool")),
            2,
        )
        .expect("b")
        .candidate
        .expect("id");
    s.confirm(b, 3).expect("b");
    s.reject(b, 4).expect("reject");
    assert_eq!(s.lesson_for("tone").expect("tone").value, "warm");
}

#[test]
fn unconfirmed_candidates_expire() {
    let mut s = store();
    s.record(
        &refl("a", Outcome::Success, 1, &[], cand("tone", "warm")),
        0,
    )
    .expect("a");
    s.maintain(15 * DAY);
    assert!(s.lessons(LessonState::Candidate).is_empty());
}

#[test]
fn domain_is_capped() {
    let mut set = Settings::default();
    set.domain_cap = 3;
    let mut s = Store::new(set, catalog()).expect("store");
    for i in 0..10 {
        s.record(
            &refl(
                &format!("t{i}"),
                Outcome::Success,
                1,
                &[],
                cand("tone", &format!("v{i}")),
            ),
            i,
        )
        .expect("t");
    }
    assert!(s.lessons(LessonState::Candidate).len() <= 3);
}

#[test]
fn code_changes_are_only_routed_never_applied() {
    let mut s = store();
    let out = s
        .record(
            &refl(
                "a",
                Outcome::Failure,
                1,
                &[],
                Some(Delta::Code {
                    request_ref: "fix-login".into(),
                }),
            ),
            0,
        )
        .expect("a");
    assert_eq!(out.code_request.as_deref(), Some("fix-login"));
    assert!(out.candidate.is_none());
    assert!(s.lessons(LessonState::Adopted).is_empty());
    assert_eq!(s.take_code_requests(), vec!["fix-login".to_string()]);
    assert!(s.take_code_requests().is_empty());
    let bad = refl(
        "a",
        Outcome::Failure,
        1,
        &[],
        Some(Delta::Code {
            request_ref: String::new(),
        }),
    );
    assert_eq!(s.record(&bad, 0).err(), Some(ReflectError::Invalid));
    for i in 0..200 {
        s.record(
            &refl(
                "a",
                Outcome::Failure,
                1,
                &[],
                Some(Delta::Code {
                    request_ref: format!("r{i}"),
                }),
            ),
            0,
        )
        .expect("r");
    }
    assert_eq!(s.take_code_requests().len(), 64);
}

#[test]
fn history_is_bounded() {
    let mut set = Settings::default();
    set.history_cap = 10;
    set.min_samples = 2;
    let mut s = Store::new(set, catalog()).expect("store");
    for i in 0..50 {
        s.record(&refl(&format!("t{i}"), Outcome::Success, 1, &[], None), 0)
            .expect("t");
    }
    assert_eq!(s.history_len(), 10);
}
