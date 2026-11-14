use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};

use crate::settings::Settings;
use crate::tests_worker_support::*;
use crate::wire::Outcome;
use crate::worker::CancelToken;

#[tokio::test(start_paused = true)]
async fn changing_a_limit_in_the_settings_json_changes_the_parallelism() {
    let mut peaks = Vec::new();
    for (raw, limit) in [
        (r#"{"max_workers":2}"#, 2_u32),
        (r#"{"max_workers":5}"#, 5),
        (r#"{"max_workers":16}"#, 16),
    ] {
        let settings = Settings::from_json(raw).expect("settings");
        let (current, peak) = (Arc::new(AtomicUsize::new(0)), Arc::new(AtomicUsize::new(0)));
        let r = rig(
            &settings,
            &[("probe", limit, false, probe(&current, &peak, 50))],
        );
        let steps = (0..16)
            .map(|i| step(&format!("s{i}"), "probe", false))
            .collect();
        let report = r
            .executor
            .run(&task(None), &plan(steps, &[]), 0, &CancelToken::new())
            .await
            .expect("run");
        assert!(report.succeeded());
        peaks.push(peak.load(Ordering::SeqCst));
    }
    assert_eq!(peaks, vec![2, 5, 16]);
}

#[test]
fn out_of_range_limits_are_refused_before_they_reach_the_runtime() {
    for raw in [
        r#"{"max_workers":0}"#,
        r#"{"max_workers":100000}"#,
        r#"{"unknown":1}"#,
    ] {
        assert!(Settings::from_json(raw).is_err());
    }
}

#[tokio::test(start_paused = true)]
async fn a_new_agent_declared_only_by_its_manifest_is_planned_and_executed() {
    let kinds: Vec<String> = (0..30).map(|i| format!("novita{i}")).collect();
    let table: Vec<(&str, u32, bool, _)> = kinds
        .iter()
        .map(|k| (k.as_str(), 2_u32, false, echo()))
        .collect();
    let r = rig(&Settings::default(), &table);
    let steps = kinds
        .iter()
        .map(|k| step(&format!("passo_{k}"), k, false))
        .collect();
    let report = r
        .executor
        .run(&task(None), &plan(steps, &[]), 0, &CancelToken::new())
        .await
        .expect("run");
    assert_eq!(
        report
            .steps
            .iter()
            .filter(|s| s.outcome == Outcome::Done)
            .count(),
        kinds.len()
    );
}

#[tokio::test(start_paused = true)]
async fn a_plan_naming_an_undeclared_agent_is_rejected_fail_closed() {
    let r = rig(&Settings::default(), &[("noto", 2, false, echo())]);
    let outcome = r
        .executor
        .run(
            &task(None),
            &plan(vec![step("x", "sconosciuto", false)], &[]),
            0,
            &CancelToken::new(),
        )
        .await;
    assert!(outcome.is_err());
}
