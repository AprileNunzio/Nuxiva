use std::path::Path;

use crate::{
    Case, Effect, EvalError, Gates, Outcome, Report, Trend, build, compare, expand, fingerprint,
    load_dir,
};

fn golden() -> Vec<Case> {
    let dir = Path::new(env!("CARGO_MANIFEST_DIR")).join("golden");
    expand(&load_dir(&dir).expect("load")).expect("expand")
}

fn outcome(case: &Case, right: bool, latency_ms: u64) -> Outcome {
    Outcome {
        case_id: case.id.clone(),
        intent: if right {
            case.expected.intent.clone()
        } else {
            "other".into()
        },
        effects: case.expected.effects.clone(),
        completed: true,
        tokens: 1_000,
        latency_ms,
    }
}

fn report(cases: &[Case], wrong_every: usize, latency_ms: u64) -> Report {
    let outcomes: Vec<Outcome> = cases
        .iter()
        .enumerate()
        .map(|(i, c)| outcome(c, wrong_every == 0 || i % wrong_every != 0, latency_ms))
        .collect();
    build(cases, &outcomes).expect("report")
}

#[test]
fn the_fingerprint_is_stable_and_order_independent() {
    let cases = golden();
    let mut reversed = cases.clone();
    reversed.reverse();
    assert_eq!(fingerprint(&cases), fingerprint(&reversed));
    let mut edited = cases.clone();
    edited[0].text.push('!');
    assert_ne!(fingerprint(&cases), fingerprint(&edited));
    assert_eq!(report(&cases, 0, 800).dataset, fingerprint(&cases));
}

#[test]
fn reports_round_trip_through_json() {
    let cases = golden();
    let original = report(&cases, 7, 800);
    let json = serde_json::to_string(&original).expect("json");
    let back: Report = serde_json::from_str(&json).expect("parse");
    assert_eq!(back, original);
}

#[test]
fn an_identical_run_is_unchanged_and_a_better_one_improves() {
    let cases = golden();
    let base = report(&cases, 5, 800);
    let same = compare(&base, &base, &Gates::default()).expect("compare");
    assert_eq!(same.trend, Trend::Unchanged);
    assert!(same.regressions.is_empty());
    let better = compare(&base, &report(&cases, 0, 800), &Gates::default()).expect("compare");
    assert_eq!(better.trend, Trend::Improved);
    assert!(better.success.change > 0.0);
}

#[test]
fn drops_slow_downs_and_new_wrong_actions_are_regressions() {
    let cases = golden();
    let base = report(&cases, 0, 800);
    let worse = compare(&base, &report(&cases, 4, 1_200), &Gates::default()).expect("compare");
    assert_eq!(worse.trend, Trend::Regressed);
    let codes: Vec<&str> = worse.regressions.iter().map(|r| r.code).collect();
    assert!(codes.contains(&"success_drop"));
    assert!(codes.contains(&"latency_up"));
    assert!(codes.contains(&"slice_drop"));
    let mut outcomes: Vec<Outcome> = cases.iter().map(|c| outcome(c, true, 800)).collect();
    outcomes[0].effects.insert(Effect::Spend);
    let unsafe_run = build(&cases, &outcomes).expect("report");
    let gates = Gates {
        max_success_drop: 5.0,
        ..Gates::default()
    };
    let result = compare(&base, &unsafe_run, &gates).expect("compare");
    assert!(
        result
            .regressions
            .iter()
            .any(|r| r.code == "wrong_actions_up")
    );
}

#[test]
fn different_datasets_cannot_be_compared() {
    let cases = golden();
    let base = report(&cases, 0, 800);
    let mut other = base.clone();
    other.dataset = "f".repeat(64);
    assert!(matches!(
        compare(&base, &other, &Gates::default()),
        Err(EvalError::Invalid("dataset_mismatch"))
    ));
    let mut legacy = base.clone();
    legacy.dataset.clear();
    assert!(compare(&legacy, &base, &Gates::default()).is_ok());
}
