use std::sync::Arc;
use std::sync::atomic::{AtomicU32, Ordering};
use std::time::Duration;

use serde_json::json;
use tokio::time::{Instant, sleep};

use nuxiva_agent_core::manifest::validate as validate_manifest;

use crate::catalog::Catalog;
use crate::settings::Settings;
use crate::supervisor::GraphGate;
use crate::tests_worker_support::*;
use crate::wire::{Outcome, Phase, WorkerErrorKind};
use crate::worker::{CancelToken, Executor, Factory};
use crate::{CODE_BUDGET, CODE_DEADLINE, CODE_LEASE, CODE_NO_KIND, CODE_PANIC};

#[tokio::test(start_paused = true)]
async fn dag_runs_in_dependency_order_and_passes_outputs_downstream() {
    let r = rig(&Settings::default(), &[("echo", 4, false, echo())]);
    let p = plan(
        ["a", "b", "c", "d"]
            .iter()
            .map(|n| step(n, "echo", false))
            .collect(),
        &[("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")],
    );
    let report = r
        .executor
        .run(&task(None), &p, 0, &CancelToken::new())
        .await
        .expect("run");
    assert!(report.succeeded());
    assert_eq!(report.steps.len(), 4);
    assert!(position(&report, "a", Phase::Done) < position(&report, "b", Phase::Started));
    assert!(position(&report, "b", Phase::Done) < position(&report, "d", Phase::Started));
    assert!(position(&report, "c", Phase::Done) < position(&report, "d", Phase::Started));
    let d = find(&report, "d").result.as_ref().expect("result");
    assert_eq!(d.output["inputs"], json!(["b", "c"]));
    assert_eq!(d.usage.tokens, 10);
    for name in ["a", "b", "c", "d"] {
        let phases: Vec<Phase> = report
            .events
            .iter()
            .filter(|e| e.step.as_str() == name)
            .map(|e| e.phase)
            .collect();
        assert_eq!(phases, vec![Phase::Queued, Phase::Started, Phase::Done]);
    }
}

#[tokio::test(start_paused = true)]
async fn a_new_kind_runs_with_no_change_to_the_executor() {
    let custom = worker(|_| async { out(json!("fatto")) });
    let r = rig(&Settings::default(), &[("novita", 1, false, custom)]);
    let report = r
        .executor
        .run(
            &task(None),
            &plan(vec![step("a", "novita", false)], &[]),
            0,
            &CancelToken::new(),
        )
        .await
        .expect("run");
    assert_eq!(
        find(&report, "a").result.as_ref().map(|x| x.output.clone()),
        Some(json!("fatto"))
    );
}

#[tokio::test(start_paused = true)]
async fn a_missing_worker_kind_fails_the_step_and_cancels_its_dependents() {
    let mut factory = Factory::new();
    factory.register("echo", echo());
    let settings = Settings::default();
    let manifests: Vec<_> = ["echo", "ghost"]
        .iter()
        .map(|k| {
            validate_manifest(&manifest(&format!("a_{k}"), k, 1, false), "x", None)
                .manifest
                .expect("m")
        })
        .collect();
    let catalog = Arc::new(Catalog::build(&manifests, &settings).expect("catalog"));
    let gate = Arc::new(GraphGate::new(&settings));
    let executor = Executor::new(catalog, Arc::new(factory), gate, settings);
    let p = plan(
        vec![step("a", "ghost", false), step("b", "echo", false)],
        &[("a", "b")],
    );
    let report = executor
        .run(&task(None), &p, 0, &CancelToken::new())
        .await
        .expect("run");
    assert_eq!(find(&report, "a").outcome, Outcome::Failed);
    assert_eq!(code(find(&report, "a")), Some(CODE_NO_KIND));
    assert_eq!(find(&report, "b").outcome, Outcome::Cancelled);
    assert_eq!(find(&report, "b").attempts, 0);
    assert!(!report.succeeded());
}

#[tokio::test(start_paused = true)]
async fn an_expired_lease_ends_in_a_typed_error_within_twice_the_lease() {
    let hang = worker(|_| async {
        sleep(Duration::from_secs(3_600)).await;
        out(json!(null))
    });
    let settings = Settings {
        lease_ms: 1_000,
        ..Settings::default()
    };
    let r = rig(&settings, &[("hang", 1, false, hang)]);
    let started = Instant::now();
    let report = r
        .executor
        .run(
            &task(None),
            &plan(vec![step("a", "hang", false)], &[]),
            0,
            &CancelToken::new(),
        )
        .await
        .expect("run");
    let elapsed = started.elapsed();
    let a = find(&report, "a");
    assert_eq!(a.outcome, Outcome::Failed);
    assert_eq!(code(a), Some(CODE_LEASE));
    assert_eq!(
        a.error.as_ref().map(|e| e.kind),
        Some(WorkerErrorKind::Timeout)
    );
    assert_eq!(a.attempts, 2);
    assert!(elapsed <= Duration::from_millis(2_010), "{elapsed:?}");
}

#[tokio::test(start_paused = true)]
async fn a_worker_that_keeps_beating_keeps_its_lease() {
    let patient = worker(|c| async move {
        for _ in 0..10 {
            sleep(Duration::from_millis(500)).await;
            c.beat();
        }
        out(json!("ok"))
    });
    let settings = Settings {
        lease_ms: 1_000,
        ..Settings::default()
    };
    let r = rig(&settings, &[("patient", 1, false, patient)]);
    let mut s = step("a", "patient", false);
    s.budget.time_ms = 60_000;
    let report = r
        .executor
        .run(&task(None), &plan(vec![s], &[]), 0, &CancelToken::new())
        .await
        .expect("run");
    assert!(report.succeeded());
    assert_eq!(find(&report, "a").attempts, 1);
}

#[tokio::test(start_paused = true)]
async fn a_lost_lease_is_reassigned_and_can_succeed() {
    let calls = Arc::new(AtomicU32::new(0));
    let seen = Arc::clone(&calls);
    let flaky = worker(move |_| {
        let first = seen.fetch_add(1, Ordering::SeqCst) == 0;
        async move {
            if first {
                sleep(Duration::from_secs(3_600)).await;
            }
            out(json!("ok"))
        }
    });
    let settings = Settings {
        lease_ms: 1_000,
        ..Settings::default()
    };
    let r = rig(&settings, &[("flaky", 1, false, flaky)]);
    let report = r
        .executor
        .run(
            &task(None),
            &plan(vec![step("a", "flaky", false)], &[]),
            0,
            &CancelToken::new(),
        )
        .await
        .expect("run");
    assert!(report.succeeded());
    assert_eq!(find(&report, "a").attempts, 2);
    assert_eq!(calls.load(Ordering::SeqCst), 2);
}

#[tokio::test(start_paused = true)]
async fn a_panicking_worker_does_not_take_down_the_plan() {
    let boom = worker(|_| async { panic!("worker failure") });
    let r = rig(
        &Settings::default(),
        &[("boom", 1, false, boom), ("echo", 1, false, echo())],
    );
    let p = plan(
        vec![step("a", "boom", false), step("b", "echo", false)],
        &[],
    );
    let report = r
        .executor
        .run(&task(None), &p, 0, &CancelToken::new())
        .await
        .expect("run");
    assert_eq!(code(find(&report, "a")), Some(CODE_PANIC));
    assert_eq!(
        find(&report, "a").error.as_ref().map(|e| e.kind),
        Some(WorkerErrorKind::Internal)
    );
    assert_eq!(find(&report, "a").attempts, 1);
    assert_eq!(find(&report, "b").outcome, Outcome::Done);
}

#[tokio::test(start_paused = true)]
async fn the_step_budget_is_a_hard_limit_and_is_not_retried() {
    let hog = worker(|c| async move {
        c.charge_tokens(60)?;
        c.charge_tokens(60)?;
        out(json!("troppo"))
    });
    let r = rig(&Settings::default(), &[("hog", 1, false, hog)]);
    let report = r
        .executor
        .run(
            &task(None),
            &plan(vec![step("a", "hog", false)], &[]),
            0,
            &CancelToken::new(),
        )
        .await
        .expect("run");
    let a = find(&report, "a");
    assert_eq!(code(a), Some(CODE_BUDGET));
    assert_eq!(a.attempts, 1);
    let calls = worker(|c| async move {
        for _ in 0..6 {
            c.charge_call()?;
        }
        out(json!(null))
    });
    let r = rig(&Settings::default(), &[("calls", 1, false, calls)]);
    let report = r
        .executor
        .run(
            &task(None),
            &plan(vec![step("a", "calls", false)], &[]),
            0,
            &CancelToken::new(),
        )
        .await
        .expect("run");
    assert_eq!(code(find(&report, "a")), Some(CODE_BUDGET));
}

#[tokio::test(start_paused = true)]
async fn the_step_deadline_stops_a_worker_that_is_alive_but_too_slow() {
    let slow = worker(|c| async move {
        loop {
            sleep(Duration::from_millis(200)).await;
            c.beat();
        }
    });
    let r = rig(&Settings::default(), &[("slow", 1, false, slow)]);
    let mut s = step("a", "slow", false);
    s.budget.time_ms = 1_000;
    let report = r
        .executor
        .run(&task(None), &plan(vec![s], &[]), 0, &CancelToken::new())
        .await
        .expect("run");
    assert_eq!(code(find(&report, "a")), Some(CODE_DEADLINE));
}
