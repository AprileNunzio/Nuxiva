use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Duration;

use tokio::time::{Instant, sleep};

use crate::settings::Settings;
use crate::tests_worker_support::*;
use crate::wire::Outcome;
use crate::worker::CancelToken;
use crate::{PressureBudget, ResourceBudget};

fn wide(kind: &str) -> Vec<crate::Step> {
    (0..8)
        .map(|i| step(&format!("s{i}"), kind, false))
        .collect()
}

async fn peak_with(rank: u8) -> usize {
    let budget = Arc::new(PressureBudget::new(8));
    budget.set_rank(rank);
    let (current, peak) = (Arc::new(AtomicUsize::new(0)), Arc::new(AtomicUsize::new(0)));
    let r = rig_with(
        &Settings::default(),
        &[("probe", 8, false, probe(&current, &peak, 50))],
        Some(budget),
    );
    let report = r
        .executor
        .run(
            &task(None),
            &plan(wide("probe"), &[]),
            0,
            &CancelToken::new(),
        )
        .await
        .expect("run");
    assert!(report.succeeded());
    peak.load(Ordering::SeqCst)
}

#[tokio::test(start_paused = true)]
async fn pressure_shrinks_parallelism_and_calm_restores_it() {
    assert_eq!(peak_with(3).await, 1);
    assert_eq!(peak_with(2).await, 2);
    assert_eq!(peak_with(1).await, 4);
    assert_eq!(peak_with(0).await, 8);
}

#[tokio::test(start_paused = true)]
async fn pressure_applied_mid_run_throttles_the_remaining_steps() {
    let budget = Arc::new(PressureBudget::new(8));
    let (current, peak) = (Arc::new(AtomicUsize::new(0)), Arc::new(AtomicUsize::new(0)));
    let r = rig_with(
        &Settings::default(),
        &[("probe", 8, false, probe(&current, &peak, 50))],
        Some(Arc::clone(&budget) as Arc<dyn ResourceBudget>),
    );
    let lever = Arc::clone(&budget);
    tokio::spawn(async move {
        sleep(Duration::from_millis(60)).await;
        lever.set_rank(3);
    });
    let more: Vec<_> = (0..24)
        .map(|i| step(&format!("s{i}"), "probe", false))
        .collect();
    let started = Instant::now();
    let report = r
        .executor
        .run(&task(None), &plan(more, &[]), 0, &CancelToken::new())
        .await
        .expect("run");
    assert!(report.succeeded());
    assert!(started.elapsed() > Duration::from_millis(500));
}

#[tokio::test(start_paused = true)]
async fn cancelling_while_queued_under_pressure_releases_every_step() {
    let budget = Arc::new(PressureBudget::new(8));
    budget.set_rank(3);
    let (current, peak) = (Arc::new(AtomicUsize::new(0)), Arc::new(AtomicUsize::new(0)));
    let r = rig_with(
        &Settings::default(),
        &[("probe", 8, false, probe(&current, &peak, 5_000))],
        Some(budget),
    );
    let cancel = CancelToken::new();
    let trigger = cancel.clone();
    tokio::spawn(async move {
        sleep(Duration::from_millis(100)).await;
        trigger.cancel();
    });
    let report = r
        .executor
        .run(&task(None), &plan(wide("probe"), &[]), 0, &cancel)
        .await
        .expect("run");
    let cancelled = report
        .steps
        .iter()
        .filter(|s| s.outcome == Outcome::Cancelled)
        .count();
    assert!(cancelled >= 7);
}

#[tokio::test(start_paused = true)]
async fn killed_workers_do_not_stop_their_neighbours_or_later_runs() {
    let doomed = worker(|c| async move {
        assert!(!c.step.id.as_str().ends_with('0'), "chaos");
        out(serde_json::json!("ok"))
    });
    let r = rig(&Settings::default(), &[("doomed", 8, false, doomed)]);
    for _ in 0..3 {
        let report = r
            .executor
            .run(
                &task(None),
                &plan(wide("doomed"), &[]),
                0,
                &CancelToken::new(),
            )
            .await
            .expect("run");
        let done = report
            .steps
            .iter()
            .filter(|s| s.outcome == Outcome::Done)
            .count();
        assert_eq!(done, 7);
        assert_eq!(code(find(&report, "s0")), Some(crate::CODE_PANIC));
    }
}

#[tokio::test(start_paused = true)]
async fn voice_runtime_stays_available_while_the_background_is_saturated_and_chaotic() {
    let hog = worker(|c| async move {
        assert!(!c.step.id.as_str().ends_with('3'), "chaos");
        sleep(Duration::from_secs(30)).await;
        out(serde_json::json!("slow"))
    });
    let background_budget = Arc::new(PressureBudget::new(8));
    background_budget.set_rank(3);
    let background = rig_with(
        &Settings::default(),
        &[("hog", 8, false, hog)],
        Some(background_budget),
    );
    let background_run = {
        let executor = Arc::clone(&background.executor);
        tokio::spawn(async move {
            executor
                .run(&task(None), &plan(wide("hog"), &[]), 0, &CancelToken::new())
                .await
        })
    };
    let voice = rig(&Settings::default(), &[("voice", 4, false, echo())]);
    let (mut served, total) = (0_u32, 2_000_u32);
    for round in 0..total {
        let started = Instant::now();
        let report = voice
            .executor
            .run(
                &task(None),
                &plan(vec![step("v", "voice", false)], &[]),
                u64::from(round),
                &CancelToken::new(),
            )
            .await
            .expect("run");
        if report.succeeded() && started.elapsed() <= Duration::from_millis(50) {
            served += 1;
        }
        if round % 100 == 0 {
            sleep(Duration::from_millis(10)).await;
        }
    }
    assert!(f64::from(served) / f64::from(total) >= 0.999);
    let report = background_run.await.expect("join").expect("run");
    assert_eq!(code(find(&report, "s3")), Some(crate::CODE_PANIC));
}
