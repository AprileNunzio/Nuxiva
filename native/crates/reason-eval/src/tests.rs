use std::collections::BTreeSet;
use std::path::Path;

use crate::{
    Case, Category, Effect, EvalError, LANGUAGES, Outcome, build, enforce_floor, expand, judge,
    load_dir, parse_outcomes,
};

fn golden() -> Vec<Case> {
    let dir = Path::new(env!("CARGO_MANIFEST_DIR")).join("golden");
    expand(&load_dir(&dir).expect("load")).expect("expand")
}

fn perfect(case: &Case) -> Outcome {
    Outcome {
        case_id: case.id.clone(),
        intent: case.expected.intent.clone(),
        effects: case.expected.effects.clone(),
        completed: true,
        tokens: 1_000,
        latency_ms: 800,
    }
}

#[test]
fn golden_set_meets_the_floor() {
    let cases = golden();
    assert_eq!(cases.len(), 300);
    enforce_floor(&cases).expect("floor");
    for lang in LANGUAGES {
        assert_eq!(cases.iter().filter(|c| c.lang == lang).count(), 50);
    }
}

#[test]
fn every_adversarial_case_carries_external_content() {
    let cases = golden();
    for case in &cases {
        assert_eq!(
            case.external_content.is_some(),
            case.category == Category::Adversarial
        );
        if case.category == Category::Adversarial {
            assert_eq!(
                case.expected.effects,
                BTreeSet::from([Effect::Read]),
                "{}",
                case.id
            );
        }
    }
}

#[test]
fn perfect_engine_scores_full_marks() {
    let cases = golden();
    let outcomes: Vec<Outcome> = cases.iter().map(perfect).collect();
    let report = build(&cases, &outcomes).expect("report");
    assert_eq!(report.overall.success, 300);
    assert_eq!(report.overall.wrong_actions, 0);
    assert!((report.overall.success_rate - 100.0).abs() < f64::EPSILON);
    assert!(report.language_gap_points.abs() < f64::EPSILON);
    assert!((report.tokens.p50 - 1_000.0).abs() < f64::EPSILON);
}

#[test]
fn unrequested_effect_is_a_wrong_action() {
    let cases = golden();
    let case = cases
        .iter()
        .find(|c| c.category == Category::Adversarial)
        .expect("case");
    let mut outcome = perfect(case);
    outcome.effects.insert(Effect::SendExternal);
    let verdict = judge(case, &outcome);
    assert!(verdict.wrong_action);
    assert!(!verdict.success);
    assert!(verdict.intent_match);
}

#[test]
fn missing_effect_or_wrong_intent_fails() {
    let cases = golden();
    let case = cases
        .iter()
        .find(|c| c.expected.effects.len() == 2)
        .expect("case");
    let mut partial = perfect(case);
    partial.effects.clear();
    assert!(!judge(case, &partial).success);
    let mut wrong = perfect(case);
    wrong.intent = "other".into();
    assert!(!judge(case, &wrong).intent_match);
    let mut unfinished = perfect(case);
    unfinished.completed = false;
    assert!(!judge(case, &unfinished).success);
}

#[test]
fn language_gap_is_measured() {
    let cases = golden();
    let outcomes: Vec<Outcome> = cases
        .iter()
        .map(|c| {
            let mut o = perfect(c);
            if c.lang == "de" && c.category == Category::Simple {
                o.intent = "unknown".into();
            }
            o
        })
        .collect();
    let report = build(&cases, &outcomes).expect("report");
    assert!(report.language_gap_points > 30.0);
    let de = report.by_language.get("de").expect("de");
    assert_eq!(de.intent_match, 32);
}

#[test]
fn missing_and_duplicate_outcomes_are_rejected() {
    let cases = golden();
    let mut outcomes: Vec<Outcome> = cases.iter().map(perfect).collect();
    let extra = outcomes.first().cloned().expect("first");
    outcomes.push(extra);
    assert!(matches!(
        build(&cases, &outcomes),
        Err(EvalError::Invalid("duplicate_outcome"))
    ));
    outcomes.truncate(299);
    assert!(matches!(
        build(&cases, &outcomes),
        Err(EvalError::Missing(_))
    ));
}

#[test]
fn malformed_scenarios_are_rejected() {
    let bad = br#"[{"id":"x","category":"simple","expected":{"intent":"a","effects":["read"]},"texts":{"it":"ciao"}}]"#;
    let scenarios = crate::parse(bad).expect("parse");
    assert!(expand(&scenarios).is_err());
    let unknown = br#"[{"id":"x","category":"simple","extra":1,"expected":{"intent":"a","effects":[]},"texts":{}}]"#;
    assert!(crate::parse(unknown).is_err());
}

#[test]
fn outcomes_parse_from_json_lines() {
    let text = b"{\"case_id\":\"a.it\",\"intent\":\"x\",\"effects\":[\"read\"],\"completed\":true,\"tokens\":5,\"latency_ms\":9}\n\n";
    let parsed = parse_outcomes(text).expect("parse");
    assert_eq!(parsed.len(), 1);
    assert!(parse_outcomes(b"not json").is_err());
}
