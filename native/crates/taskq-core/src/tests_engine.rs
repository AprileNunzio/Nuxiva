use std::path::PathBuf;
use std::sync::Arc;
use std::sync::atomic::{AtomicU32, AtomicUsize, Ordering};
use std::time::{Duration, Instant};

use crate::tests::spec;
use crate::*;

type Handler = dyn Fn(TaskSpec, CancelToken, Progress) -> BoxFuture<Result<Vec<String>, ErrorPayload>>
    + Send
    + Sync;

struct FnExec(Box<Handler>);

impl Executor for FnExec {
    fn run(
        &self,
        spec: TaskSpec,
        cancel: CancelToken,
        progress: Progress,
    ) -> BoxFuture<Result<Vec<String>, ErrorPayload>> {
        (self.0)(spec, cancel, progress)
    }
}

fn exec<F>(f: F) -> Arc<dyn Executor>
where
    F: Fn(TaskSpec, CancelToken, Progress) -> BoxFuture<Result<Vec<String>, ErrorPayload>>
        + Send
        + Sync
        + 'static,
{
    Arc::new(FnExec(Box::new(f)))
}

fn engine(settings: Settings, executor: Arc<dyn Executor>) -> Engine {
    Engine::start(
        settings,
        executor,
        Box::new(MemoryJournal::new()),
        Arc::new(SystemClock::new()),
    )
    .expect("engine")
}

fn wait_state(e: &Engine, id: &str, want: TaskState) -> TaskEvent {
    let end = Instant::now() + Duration::from_secs(10);
    loop {
        if let Some(ev) = e.status(id) {
            if ev.state == want {
                return ev;
            }
        }
        assert!(
            Instant::now() < end,
            "timeout waiting {id} {want:?}: {:?}",
            e.status(id)
        );
        std::thread::sleep(Duration::from_millis(5));
    }
}

fn temp(name: &str) -> PathBuf {
    static N: AtomicU32 = AtomicU32::new(0);
    let dir = std::env::temp_dir().join(format!(
        "nuxiva-taskq-{}-{}",
        std::process::id(),
        N.fetch_add(1, Ordering::SeqCst)
    ));
    std::fs::create_dir_all(&dir).expect("dir");
    dir.join(name)
}

fn ok_after(ms: u64) -> Arc<dyn Executor> {
    exec(move |s, _c, _p| {
        Box::pin(async move {
            tokio::time::sleep(Duration::from_millis(ms)).await;
            Ok(vec![format!("ev:{}", s.id)])
        })
    })
}

#[test]
fn runs_task_and_reports_evidence() {
    let e = engine(Settings::default(), ok_after(5));
    assert_eq!(
        e.submit(spec("a", Class::Background, 1)),
        Ok(Submitted::Accepted)
    );
    let ev = wait_state(&e, "a", TaskState::Done);
    assert_eq!(ev.progress, 100);
    let events = e.drain_events(100);
    assert!(events.iter().any(|x| x.state == TaskState::Running));
    assert!(
        events
            .iter()
            .any(|x| x.state == TaskState::Done && x.evidence == vec!["ev:a".to_string()])
    );
}

#[test]
fn submit_json_validates() {
    let e = engine(Settings::default(), ok_after(1));
    assert_eq!(e.submit_json("{}"), Err(TaskqError::Parse));
    let text = spec("j", Class::Interactive, 3).to_json().expect("json");
    assert_eq!(e.submit_json(&text), Ok(Submitted::Accepted));
    wait_state(&e, "j", TaskState::Done);
}

#[test]
fn dependencies_run_in_order() {
    let order = Arc::new(std::sync::Mutex::new(Vec::<String>::new()));
    let seen = Arc::clone(&order);
    let e = engine(
        Settings::default(),
        exec(move |s, _c, _p| {
            let seen = Arc::clone(&seen);
            Box::pin(async move {
                tokio::time::sleep(Duration::from_millis(10)).await;
                seen.lock().expect("lock").push(s.id);
                Ok(vec![])
            })
        }),
    );
    e.submit(spec("a", Class::Background, 1)).expect("a");
    let mut b = spec("b", Class::Background, 9);
    b.deps = vec!["a".into()];
    e.submit(b).expect("b");
    wait_state(&e, "b", TaskState::Done);
    assert_eq!(
        *order.lock().expect("lock"),
        vec!["a".to_string(), "b".to_string()]
    );
}

#[test]
fn cancel_stops_running_task() {
    let observed = Arc::new(AtomicU32::new(0));
    let flag = Arc::clone(&observed);
    let e = engine(
        Settings::default(),
        exec(move |_s, c, _p| {
            let flag = Arc::clone(&flag);
            Box::pin(async move {
                c.cancelled().await;
                flag.fetch_add(1, Ordering::SeqCst);
                Err(ErrorPayload::new("taskq.cancelled", false))
            })
        }),
    );
    e.submit(spec("a", Class::Background, 1)).expect("a");
    wait_state(&e, "a", TaskState::Running);
    e.cancel("a").expect("cancel");
    wait_state(&e, "a", TaskState::Cancelled);
    assert_eq!(e.cancel("a"), Err(TaskqError::Terminal));
    assert_eq!(e.cancel("zz"), Err(TaskqError::NotFound));
}

#[test]
fn cancel_hard_kills_uncooperative_task() {
    let e = engine(
        Settings::default(),
        exec(|_s, _c, _p| {
            Box::pin(async move {
                tokio::time::sleep(Duration::from_secs(3600)).await;
                Ok(vec![])
            })
        }),
    );
    e.submit(spec("a", Class::Background, 1)).expect("a");
    wait_state(&e, "a", TaskState::Running);
    e.cancel("a").expect("cancel");
    wait_state(&e, "a", TaskState::Cancelled);
    assert_eq!(e.stats().background.running, 0);
}

#[test]
fn transient_failure_retries_then_succeeds() {
    let calls = Arc::new(AtomicU32::new(0));
    let counter = Arc::clone(&calls);
    let mut settings = Settings::default();
    settings.backoff_base_ms = 10;
    settings.backoff_cap_ms = 50;
    let e = engine(
        settings,
        exec(move |_s, _c, _p| {
            let n = counter.fetch_add(1, Ordering::SeqCst);
            Box::pin(async move {
                if n == 0 {
                    Err(ErrorPayload::new("net.reset", true))
                } else {
                    Ok(vec![])
                }
            })
        }),
    );
    e.submit(spec("a", Class::Background, 1)).expect("a");
    let ev = wait_state(&e, "a", TaskState::Done);
    assert_eq!(ev.attempt, 2);
    assert_eq!(calls.load(Ordering::SeqCst), 2);
}

#[test]
fn panic_is_isolated() {
    let e = engine(
        Settings::default(),
        exec(|s, _c, _p| {
            Box::pin(async move {
                assert!(s.id != "boom", "boom");
                Ok(vec![])
            })
        }),
    );
    e.submit(spec("boom", Class::Background, 1)).expect("boom");
    let ev = wait_state(&e, "boom", TaskState::Failed);
    assert_eq!(ev.error.expect("err").code, "taskq.panic");
    e.submit(spec("fine", Class::Background, 1)).expect("fine");
    wait_state(&e, "fine", TaskState::Done);
}

#[test]
fn wall_budget_is_enforced() {
    let e = engine(
        Settings::default(),
        exec(|_s, _c, _p| {
            Box::pin(async move {
                tokio::time::sleep(Duration::from_secs(3600)).await;
                Ok(vec![])
            })
        }),
    );
    let mut s = spec("slow", Class::Background, 1);
    s.budget.wall_ms = 50;
    e.submit(s).expect("slow");
    let ev = wait_state(&e, "slow", TaskState::Failed);
    assert_eq!(ev.error.expect("err").code, "taskq.deadline");
}

#[test]
fn progress_is_visible_while_running() {
    let e = engine(
        Settings::default(),
        exec(|_s, c, p| {
            Box::pin(async move {
                p.set(40);
                c.cancelled().await;
                Ok(vec![])
            })
        }),
    );
    e.submit(spec("a", Class::Interactive, 1)).expect("a");
    wait_state(&e, "a", TaskState::Running);
    let end = Instant::now() + Duration::from_secs(5);
    while e.status("a").map(|x| x.progress) != Some(40) {
        assert!(Instant::now() < end);
        std::thread::sleep(Duration::from_millis(5));
    }
    e.cancel("a").expect("cancel");
}

#[test]
fn voice_class_is_not_starved_by_backlog() {
    let mut settings = Settings::default();
    settings.background.capacity = 2_000;
    settings.background.concurrency = 4;
    let running = Arc::new(AtomicUsize::new(0));
    let peak = Arc::new(AtomicUsize::new(0));
    let (r, p) = (Arc::clone(&running), Arc::clone(&peak));
    let e = engine(
        settings,
        exec(move |s, _c, _p| {
            let (r, p) = (Arc::clone(&r), Arc::clone(&p));
            Box::pin(async move {
                let now = r.fetch_add(1, Ordering::SeqCst) + 1;
                if s.class == Class::Background {
                    p.fetch_max(now, Ordering::SeqCst);
                    tokio::time::sleep(Duration::from_millis(20)).await;
                }
                r.fetch_sub(1, Ordering::SeqCst);
                Ok(vec![])
            })
        }),
    );
    for i in 0..1_000 {
        e.submit(spec(&format!("bg{i}"), Class::Background, 1))
            .expect("bg");
    }
    let started = Instant::now();
    e.submit(spec("voice", Class::Voice, 9)).expect("voice");
    wait_state(&e, "voice", TaskState::Done);
    assert!(
        started.elapsed() < Duration::from_millis(500),
        "{:?}",
        started.elapsed()
    );
    assert!(e.stats().background.queued > 100);
    assert!(peak.load(Ordering::SeqCst) <= 8);
}

#[test]
fn submission_latency_stays_low_under_load() {
    let mut settings = Settings::default();
    settings.background.capacity = 5_000;
    let e = engine(
        settings,
        exec(|_s, c, _p| {
            Box::pin(async move {
                c.cancelled().await;
                Ok(vec![])
            })
        }),
    );
    let mut worst = Duration::ZERO;
    for i in 0..3_000 {
        let t = Instant::now();
        e.submit(spec(&format!("t{i}"), Class::Background, (i % 10) as u8))
            .expect("submit");
        worst = worst.max(t.elapsed());
    }
    assert!(worst < Duration::from_millis(250), "{worst:?}");
}

#[test]
fn resumes_after_crash_without_losing_tasks() {
    let path = temp("journal.log");
    let blocked = exec(|_s, c, _p| {
        Box::pin(async move {
            c.cancelled().await;
            Ok(vec![])
        })
    });
    {
        let journal = FileJournal::open(&path, 1 << 20).expect("journal");
        let e = Engine::start(
            Settings::default(),
            blocked,
            Box::new(journal),
            Arc::new(SystemClock::new()),
        )
        .expect("e1");
        for i in 0..20 {
            e.submit(spec(&format!("t{i}"), Class::Background, 1))
                .expect("submit");
        }
        let mut high = spec("risky", Class::Maintenance, 1);
        high.risk_max = Risk::High;
        e.submit(high).expect("risky");
        wait_state(&e, "risky", TaskState::Running);
    }
    let journal = FileJournal::open(&path, 1 << 20).expect("reopen");
    let e = Engine::start(
        Settings::default(),
        ok_after(1),
        Box::new(journal),
        Arc::new(SystemClock::new()),
    )
    .expect("e2");
    for i in 0..20 {
        wait_state(&e, &format!("t{i}"), TaskState::Done);
    }
    let risky = e.status("risky").expect("risky");
    assert_eq!(risky.state, TaskState::Failed);
    assert_eq!(risky.error.expect("err").code, "taskq.interrupted");
}

#[test]
fn journal_detects_tampering() {
    let path = temp("journal.log");
    {
        let mut j = FileJournal::open(&path, 1 << 20).expect("journal");
        let mut q = Queue::new(Settings::default());
        q.submit(spec("a", Class::Background, 1), 0).expect("a");
        q.submit(spec("b", Class::Background, 1), 0).expect("b");
        j.append(0, &q.drain()).expect("append");
    }
    let text = std::fs::read_to_string(&path).expect("read");
    std::fs::write(&path, text.replacen("\"priority\":1", "\"priority\":9", 1)).expect("write");
    assert_eq!(
        FileJournal::open(&path, 1 << 20).err(),
        Some(TaskqError::Tamper)
    );
}

#[test]
fn journal_drops_torn_tail_and_keeps_going() {
    let path = temp("journal.log");
    {
        let mut j = FileJournal::open(&path, 1 << 20).expect("journal");
        let mut q = Queue::new(Settings::default());
        q.submit(spec("a", Class::Background, 1), 0).expect("a");
        j.append(0, &q.drain()).expect("append");
    }
    let mut text = std::fs::read_to_string(&path).expect("read");
    text.push_str("{\"seq\":2,\"at\":0,\"pre");
    std::fs::write(&path, text).expect("write");
    let mut j = FileJournal::open(&path, 1 << 20).expect("reopen");
    assert_eq!(j.load().expect("load").len(), 2);
    let mut q = Queue::new(Settings::default());
    q.submit(spec("b", Class::Background, 1), 0).expect("b");
    j.append(1, &q.drain()).expect("append more");
    let mut again = FileJournal::open(&path, 1 << 20).expect("again");
    assert_eq!(again.load().expect("load").len(), 4);
}

#[test]
fn journal_is_bounded_and_compacts() {
    let path = temp("journal.log");
    let mut settings = Settings::default();
    settings.retain_terminal = 4;
    let journal = FileJournal::open(&path, 40_000).expect("journal");
    let e = Engine::start(
        settings,
        ok_after(0),
        Box::new(journal),
        Arc::new(SystemClock::new()),
    )
    .expect("e");
    for i in 0..200 {
        e.submit(spec(&format!("t{i}"), Class::Background, 1))
            .expect("submit");
        wait_state(&e, &format!("t{i}"), TaskState::Done);
    }
    assert!(std::fs::metadata(&path).expect("meta").len() <= 40_000);
    assert_eq!(e.stats().journal_errors, 0);
    drop(e);
    assert!(FileJournal::open(&path, 40_000).is_ok());
}

#[test]
fn journal_failure_rejects_submit() {
    let path = temp("journal.log");
    let journal = FileJournal::open(&path, 300).expect("journal");
    let e = Engine::start(
        Settings::default(),
        ok_after(0),
        Box::new(journal),
        Arc::new(SystemClock::new()),
    )
    .expect("e");
    let mut rejected = false;
    for i in 0..20 {
        if e.submit(spec(&format!("t{i}"), Class::Background, 1))
            .is_err()
        {
            rejected = true;
            break;
        }
    }
    assert!(rejected);
}

#[test]
fn shutdown_rejects_new_work() {
    let mut e = engine(Settings::default(), ok_after(1));
    e.shutdown();
    assert_eq!(
        e.submit(spec("a", Class::Voice, 1)),
        Err(TaskqError::Shutdown)
    );
}

#[cfg(unix)]
#[test]
fn journal_file_is_private() {
    use std::os::unix::fs::PermissionsExt;
    let path = temp("journal.log");
    let _journal = FileJournal::open(&path, 1 << 20).expect("journal");
    let mode = std::fs::metadata(&path).expect("meta").permissions().mode();
    assert_eq!(mode & 0o077, 0);
}
