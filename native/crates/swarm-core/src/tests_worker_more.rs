use std::sync::Arc;
use std::sync::atomic::{AtomicU32, AtomicUsize, Ordering};
use std::time::Duration;

use serde_json::json;
use tokio::time::{Instant, sleep};

use crate::error::SwarmError;
use crate::settings::Settings;
use crate::tests_worker_support::*;
use crate::wire::{Digest, Ident, Outcome, Step, WorkerErrorKind};
use crate::worker::{CancelToken, StepContext, Worker};
use crate::{
    CODE_BUDGET, CODE_CANCELLED, CODE_DEADLINE, CODE_DEPTH, CODE_GRAPH, CODE_LEASE, CODE_NO_KIND,
    CODE_OUTPUT, CODE_PANIC, CODE_STALE,
};

#[tokio::test(start_paused = true)]
async fn cancellation_stops_running_steps_and_skips_the_rest() {
    let loopy = worker(|c| async move {
        loop {
            sleep(Duration::from_millis(100)).await;
            c.beat();
            c.check_cancel()?;
        }
    });
    let r = rig(
        &Settings::default(),
        &[("loopy", 1, false, loopy), ("echo", 1, false, echo())],
    );
    let p = plan(
        vec![step("a", "loopy", false), step("b", "echo", false)],
        &[("a", "b")],
    );
    let cancel = CancelToken::new();
    let trigger = cancel.clone();
    tokio::spawn(async move {
        sleep(Duration::from_millis(350)).await;
        trigger.cancel();
    });
    let started = Instant::now();
    let report = r
        .executor
        .run(&task(None), &p, 0, &cancel)
        .await
        .expect("run");
    assert!(started.elapsed() <= Duration::from_millis(400));
    assert_eq!(find(&report, "a").outcome, Outcome::Cancelled);
    assert_eq!(find(&report, "b").outcome, Outcome::Cancelled);
    assert_eq!(code(find(&report, "a")), Some(CODE_CANCELLED));
    let before = CancelToken::new();
    before.cancel();
    let report = r
        .executor
        .run(&task(None), &p, 0, &before)
        .await
        .expect("run");
    assert_eq!(find(&report, "a").outcome, Outcome::Cancelled);
}

#[tokio::test(start_paused = true)]
async fn graph_steps_never_start_without_a_fresh_consulted_reference() {
    let started = Arc::new(AtomicU32::new(0));
    let seen = Arc::clone(&started);
    let guarded = worker(move |_| {
        seen.fetch_add(1, Ordering::SeqCst);
        async { out(json!("ok")) }
    });
    let r = rig(&Settings::default(), &[("guarded", 1, true, guarded)]);
    let p = plan(vec![step("a", "guarded", true)], &[]);
    let report = r
        .executor
        .run(&task(None), &p, 0, &CancelToken::new())
        .await
        .expect("run");
    assert_eq!(code(find(&report, "a")), Some(CODE_GRAPH));
    assert_eq!(
        find(&report, "a").error.as_ref().map(|e| e.kind),
        Some(WorkerErrorKind::GraphNotConsulted)
    );
    let reference = Digest::try_from("b".repeat(64)).expect("digest");
    let with = task(Some(reference.clone()));
    let report = r
        .executor
        .run(&with, &p, 5, &CancelToken::new())
        .await
        .expect("run");
    assert_eq!(code(find(&report, "a")), Some(CODE_GRAPH));
    r.gate.issue(reference, 10);
    let report = r
        .executor
        .run(&with, &p, 11, &CancelToken::new())
        .await
        .expect("run");
    assert!(report.succeeded());
    let late = 10 + Settings::default().graph_ref_ttl_ms + 1;
    let report = r
        .executor
        .run(&with, &p, late, &CancelToken::new())
        .await
        .expect("run");
    assert_eq!(code(find(&report, "a")), Some(CODE_STALE));
    assert_eq!(started.load(Ordering::SeqCst), 1);
}

#[tokio::test(start_paused = true)]
async fn redelegation_depth_is_capped() {
    let delegate = worker(|c| async move {
        let mut current = c.task.clone();
        let mut made = 0_u32;
        loop {
            let next = StepContext {
                task: current.clone(),
                step: c.step.clone(),
                inputs: c.inputs.clone(),
                cancel: c.cancel.clone(),
                meter: Arc::clone(&c.meter),
                beat: c.beat.clone(),
                depth_limit: c.depth_limit,
            };
            match next.child(id("lavoro"), id("in.2")) {
                Ok(child) => {
                    current = child;
                    made += 1;
                }
                Err(error) => {
                    return if made == 2 {
                        Err(error)
                    } else {
                        out(json!(made))
                    };
                }
            }
        }
    });
    let r = rig(&Settings::default(), &[("delegate", 1, false, delegate)]);
    let report = r
        .executor
        .run(
            &task(None),
            &plan(vec![step("a", "delegate", false)], &[]),
            0,
            &CancelToken::new(),
        )
        .await
        .expect("run");
    assert_eq!(code(find(&report, "a")), Some(CODE_DEPTH));
    assert_eq!(
        find(&report, "a").error.as_ref().map(|e| e.kind),
        Some(WorkerErrorKind::Denied)
    );
}

#[tokio::test(start_paused = true)]
async fn oversized_output_is_refused() {
    let big = worker(|_| async { out(json!("x".repeat(300 * 1024))) });
    let r = rig(&Settings::default(), &[("big", 1, false, big)]);
    let report = r
        .executor
        .run(
            &task(None),
            &plan(vec![step("a", "big", false)], &[]),
            0,
            &CancelToken::new(),
        )
        .await
        .expect("run");
    assert_eq!(code(find(&report, "a")), Some(CODE_OUTPUT));
}

#[tokio::test(start_paused = true)]
async fn invalid_plans_are_rejected_before_anything_runs() {
    let r = rig(&Settings::default(), &[("echo", 1, false, echo())]);
    let bad = plan(
        vec![step("a", "echo", false), step("b", "echo", false)],
        &[("a", "b"), ("b", "a")],
    );
    assert_eq!(
        r.executor
            .run(&task(None), &bad, 0, &CancelToken::new())
            .await
            .err(),
        Some(SwarmError::Cycle)
    );
    let mut unknown = step("a", "echo", false);
    unknown.worker_template = id("fantasma");
    assert_eq!(
        r.executor
            .run(
                &task(None),
                &plan(vec![unknown], &[]),
                0,
                &CancelToken::new()
            )
            .await
            .err(),
        Some(SwarmError::UnknownTemplate)
    );
}

#[tokio::test(start_paused = true)]
async fn per_template_and_global_concurrency_are_enforced() {
    let (current, peak) = (Arc::new(AtomicUsize::new(0)), Arc::new(AtomicUsize::new(0)));
    let r = rig(
        &Settings::default(),
        &[("probe", 2, false, probe(&current, &peak, 1_000))],
    );
    let steps: Vec<Step> = (0..6)
        .map(|i| step(&format!("s{i}"), "probe", false))
        .collect();
    let report = r
        .executor
        .run(&task(None), &plan(steps, &[]), 0, &CancelToken::new())
        .await
        .expect("run");
    assert!(report.succeeded());
    assert_eq!(peak.load(Ordering::SeqCst), 2);
    let (current, peak) = (Arc::new(AtomicUsize::new(0)), Arc::new(AtomicUsize::new(0)));
    let settings = Settings {
        max_workers: 3,
        ..Settings::default()
    };
    let r = rig(
        &settings,
        &[("probe", 3, false, probe(&current, &peak, 1_000))],
    );
    let mut runs = Vec::new();
    for _ in 0..4 {
        let executor = Arc::clone(&r.executor);
        let steps: Vec<Step> = (0..3)
            .map(|i| step(&format!("s{i}"), "probe", false))
            .collect();
        runs.push(tokio::spawn(async move {
            executor
                .run(&task(None), &plan(steps, &[]), 0, &CancelToken::new())
                .await
        }));
    }
    for run in runs {
        assert!(run.await.expect("join").expect("run").succeeded());
    }
    assert_eq!(peak.load(Ordering::SeqCst), 3);
}

#[tokio::test(start_paused = true)]
async fn a_thousand_concurrent_workers_stay_light() {
    let (current, peak) = (Arc::new(AtomicUsize::new(0)), Arc::new(AtomicUsize::new(0)));
    let settings = Settings {
        max_workers: 1_000,
        ..Settings::default()
    };
    let kinds: Vec<(String, u32, bool, Arc<dyn Worker>)> = (0..4)
        .map(|i| {
            (
                format!("probe{i}"),
                250,
                false,
                probe(&current, &peak, 1_000),
            )
        })
        .collect();
    let refs: Vec<(&str, u32, bool, Arc<dyn Worker>)> = kinds
        .iter()
        .map(|(k, l, g, w)| (k.as_str(), *l, *g, Arc::clone(w)))
        .collect();
    let r = rig(&settings, &refs);
    let before = resident_kib();
    let mut runs = Vec::new();
    for i in 0..1_000 {
        let executor = Arc::clone(&r.executor);
        let p = plan(vec![step("a", &format!("probe{}", i % 4), false)], &[]);
        runs.push(tokio::spawn(async move {
            executor.run(&task(None), &p, 0, &CancelToken::new()).await
        }));
    }
    sleep(Duration::from_millis(500)).await;
    let during = resident_kib();
    for run in runs {
        assert!(run.await.expect("join").expect("run").succeeded());
    }
    assert_eq!(peak.load(Ordering::SeqCst), 1_000);
    if let (Some(before), Some(during)) = (before, during) {
        assert!(
            during.saturating_sub(before) < 50 * 1024,
            "{} KiB",
            during.saturating_sub(before)
        );
    }
}

#[test]
fn every_known_error_code_is_a_valid_identifier() {
    for code in [
        CODE_BUDGET,
        CODE_CANCELLED,
        CODE_DEADLINE,
        CODE_DEPTH,
        CODE_GRAPH,
        CODE_LEASE,
        CODE_NO_KIND,
        CODE_OUTPUT,
        CODE_PANIC,
        CODE_STALE,
    ] {
        assert!(Ident::new(code).is_ok(), "{code}");
    }
}

#[test]
fn settings_bound_the_worker_runtime() {
    let settings = Settings {
        lease_ms: 0,
        ..Settings::default()
    };
    assert_eq!(settings.validate(), Err(SwarmError::Settings));
    let settings = Settings {
        step_attempts: 0,
        ..Settings::default()
    };
    assert_eq!(settings.validate(), Err(SwarmError::Settings));
    let settings = Settings {
        step_attempts: 6,
        ..Settings::default()
    };
    assert_eq!(settings.validate(), Err(SwarmError::Settings));
}
