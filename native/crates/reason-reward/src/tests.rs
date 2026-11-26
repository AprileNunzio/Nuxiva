use std::collections::BTreeMap;

use model_router::{Placement, Profile, Task};
use reason_eval::Verdict;
use reason_exec::{Report, Status, StepReport};

use crate::{
    Key, Learner, Ledger, MAX_STEP_BPS, MIN_TRIALS, Signal, StepOutcome, Subject, WINDOW, apply,
    from_report, from_verdict, score, task_of,
};

fn key(id: &str) -> Key {
    Key::new(Subject::Model, id, "understand").expect("key")
}

fn good() -> Signal {
    Signal::Tests {
        passed: 10,
        total: 10,
    }
}

fn bad() -> Signal {
    Signal::Command {
        exit_code: 2,
        timed_out: false,
    }
}

fn profile(quality: u16) -> Profile {
    Profile {
        id: "qwen3:4b-q4".into(),
        placement: Placement::Local,
        context_tokens: 8_192,
        micro_per_1k_in: 0,
        micro_per_1k_out: 0,
        latency_ms: 400,
        quality_bps: BTreeMap::from([(Task::Understand, quality)]),
    }
}

#[test]
fn verifiable_signals_map_to_bounded_scores() {
    assert_eq!(score(&[good()]).expect("score").score_bps, 10_000);
    assert_eq!(score(&[bad()]).expect("score").score_bps, -10_000);
    let half = score(&[Signal::Tests {
        passed: 5,
        total: 10,
    }])
    .expect("score");
    assert_eq!(half.score_bps, 0);
    assert_eq!(half.gain(), 5_000);
    let doc = score(&[Signal::Document {
        valid: true,
        issues: 3,
    }])
    .expect("score");
    assert_eq!(doc.score_bps, 7_000);
    let timeout = score(&[Signal::Command {
        exit_code: 0,
        timed_out: true,
    }])
    .expect("score");
    assert_eq!(timeout.score_bps, -10_000);
}

#[test]
fn a_wrong_action_vetoes_every_other_success() {
    let reward = score(&[
        good(),
        good(),
        Signal::Intent {
            matched: true,
            completed: true,
            wrong_action: true,
        },
    ])
    .expect("score");
    assert!(reward.unsafe_action);
    assert_eq!(reward.score_bps, -10_000);
}

#[test]
fn human_choices_are_neutral_and_unverified_rewards_are_not_learned() {
    let reward = score(&[Signal::Step {
        outcome: StepOutcome::Denied,
    }])
    .expect("score");
    assert!(!reward.verified);
    let mut ledger = Ledger::new();
    ledger.record(&key("m"), &reward).expect("record");
    assert!(ledger.is_empty());
}

#[test]
fn malformed_signals_are_refused() {
    for signal in [
        Signal::Tests {
            passed: 3,
            total: 2,
        },
        Signal::Tests {
            passed: 0,
            total: 0,
        },
        Signal::Intent {
            matched: true,
            completed: false,
            wrong_action: false,
        },
        Signal::Document {
            valid: true,
            issues: 1_000_000,
        },
    ] {
        assert!(score(&[signal]).is_err(), "{signal:?}");
    }
}

#[test]
fn keys_reject_injection_and_oversized_names() {
    assert!(Key::new(Subject::Model, "qwen3:4b-q4", "understand").is_ok());
    assert!(Key::new(Subject::Model, "", "understand").is_err());
    assert!(Key::new(Subject::Model, "a b", "understand").is_err());
    assert!(Key::new(Subject::Model, "m", "Plan").is_err());
    assert!(Key::new(Subject::Capability, &"x".repeat(65), "plan").is_err());
}

#[test]
fn the_window_keeps_recent_experience_and_stays_bounded() {
    let mut learner = Learner::default();
    let k = key("m");
    for _ in 0..(WINDOW * 3) {
        learner.observe(&k, &[bad()]).expect("observe");
    }
    for _ in 0..WINDOW {
        learner.observe(&k, &[good()]).expect("observe");
    }
    let tally = learner.ledger().get(&k).expect("tally");
    assert!(tally.trials <= WINDOW);
    assert!(tally.estimate_bps() > 6_000, "{}", tally.estimate_bps());
}

#[test]
fn proposals_move_slowly_and_need_evidence() {
    let mut learner = Learner::default();
    let k = key("m");
    for _ in 0..(MIN_TRIALS - 1) {
        learner.observe(&k, &[good()]).expect("observe");
    }
    assert!(learner.propose(|_| Some(6_000)).is_empty());
    learner.observe(&k, &[good()]).expect("observe");
    let proposals = learner.propose(|_| Some(6_000));
    assert_eq!(proposals.len(), 1);
    assert_eq!(proposals[0].proposed_bps, 6_000 + MAX_STEP_BPS);
    assert!(!proposals[0].quarantine);
    assert!(learner.propose(|_| None).is_empty());
}

#[test]
fn repeated_unsafe_actions_quarantine_the_subject() {
    let mut learner = Learner::default();
    let k = key("m");
    for i in 0..40 {
        let wrong = i % 10 == 0;
        learner
            .observe(
                &k,
                &[Signal::Intent {
                    matched: true,
                    completed: true,
                    wrong_action: wrong,
                }],
            )
            .expect("observe");
    }
    let proposals = learner.propose(|_| Some(9_000));
    assert_eq!(proposals.len(), 1);
    assert!(proposals[0].quarantine);
    assert_eq!(proposals[0].proposed_bps, 0);
}

#[test]
fn adjustments_update_router_profiles_only_when_valid() {
    let mut learner = Learner::default();
    let k = key("qwen3:4b-q4");
    for _ in 0..MIN_TRIALS {
        learner.observe(&k, &[good()]).expect("observe");
    }
    let mut p = profile(6_000);
    let proposals = learner.propose(|_| Some(p.quality(Task::Understand)));
    let task = task_of(&proposals[0].key.task).expect("task");
    apply(&mut p, task, &proposals[0]).expect("apply");
    assert_eq!(p.quality(Task::Understand), 6_300);
    let mut forged = proposals[0].clone();
    forged.proposed_bps = 20_000;
    assert!(apply(&mut p, task, &forged).is_err());
    assert_eq!(p.quality(Task::Understand), 6_300);
}

#[test]
fn ledgers_round_trip_and_reject_tampering() {
    let mut learner = Learner::default();
    learner.observe(&key("m"), &[good()]).expect("observe");
    let json = learner.ledger().to_json().expect("json");
    let back = Ledger::from_json(json.as_bytes()).expect("parse");
    assert_eq!(&back, learner.ledger());
    let forged = r#"[{"key":{"subject":"model","id":"m","task":"plan"},"tally":{"trials":1,"gain_sum":99999,"unsafe_count":0}}]"#;
    assert!(Ledger::from_json(forged.as_bytes()).is_err());
    let extra = r#"[{"key":{"subject":"model","id":"m","task":"plan"},"tally":{"trials":1,"gain_sum":1,"unsafe_count":0},"x":1}]"#;
    assert!(Ledger::from_json(extra.as_bytes()).is_err());
    let duplicate = r#"[{"key":{"subject":"model","id":"m","task":"plan"},"tally":{"trials":1,"gain_sum":1,"unsafe_count":0}},{"key":{"subject":"model","id":"m","task":"plan"},"tally":{"trials":1,"gain_sum":1,"unsafe_count":0}}]"#;
    assert!(Ledger::from_json(duplicate.as_bytes()).is_err());
}

#[test]
fn executor_reports_and_eval_verdicts_become_signals() {
    let report = Report {
        steps: vec![
            StepReport {
                step: "a".into(),
                status: Status::Done("ok".into()),
                attempts: 1,
            },
            StepReport {
                step: "b".into(),
                status: Status::Failed,
                attempts: 3,
            },
            StepReport {
                step: "c".into(),
                status: Status::Denied,
                attempts: 0,
            },
        ],
    };
    let reward = score(&from_report(&report)).expect("score");
    assert_eq!(reward.signals, 2);
    assert_eq!(reward.score_bps, 0);
    let verdict = Verdict {
        intent_match: true,
        success: true,
        wrong_action: false,
    };
    assert_eq!(
        score(&[from_verdict(&verdict, true)])
            .expect("score")
            .score_bps,
        10_000
    );
    assert_eq!(
        score(&[from_verdict(&verdict, false)])
            .expect("score")
            .score_bps,
        -10_000
    );
}
