use crate::*;

pub(crate) fn budget() -> Budget {
    Budget {
        wall_ms: 1_000,
        tokens: 0,
        tool_calls: 0,
        cpu_ms: 0,
    }
}

pub(crate) fn spec(id: &str, class: Class, priority: u8) -> TaskSpec {
    TaskSpec {
        schema_version: SCHEMA_VERSION,
        id: id.into(),
        parent: None,
        kind: "job".into(),
        class,
        priority,
        deps: Vec::new(),
        scope: Vec::new(),
        budget: budget(),
        risk_max: Risk::Low,
        input_ref: "ref".into(),
        idem_key: None,
    }
}

fn queue() -> Queue {
    Queue::new(Settings::default())
}

fn popped(q: &mut Queue, class: Class, now: u64) -> Option<String> {
    q.pop(class, now).map(|d| d.spec.id)
}

#[test]
fn priority_orders_dispatch() {
    let mut q = queue();
    q.submit(spec("low", Class::Background, 1), 0).expect("low");
    q.submit(spec("high", Class::Background, 9), 0)
        .expect("high");
    assert_eq!(
        popped(&mut q, Class::Background, 0).as_deref(),
        Some("high")
    );
}

#[test]
fn fifo_within_same_priority() {
    let mut q = queue();
    for i in 0..3 {
        q.submit(spec(&format!("t{i}"), Class::Interactive, 5), 0)
            .expect("submit");
    }
    assert_eq!(popped(&mut q, Class::Interactive, 0).as_deref(), Some("t0"));
    q.complete("t0", vec![], 0).expect("done");
    assert_eq!(popped(&mut q, Class::Interactive, 0).as_deref(), Some("t1"));
}

#[test]
fn aging_prevents_starvation() {
    let mut s = Settings::default();
    s.background.concurrency = 1;
    let mut q = Queue::new(s);
    q.submit(spec("old", Class::Background, 0), 0).expect("old");
    q.submit(spec("new", Class::Background, 3), 10_000)
        .expect("new");
    assert_eq!(
        popped(&mut q, Class::Background, 10_000).as_deref(),
        Some("old")
    );
}

#[test]
fn concurrency_limit_per_class() {
    let mut s = Settings::default();
    s.background.concurrency = 1;
    let mut q = Queue::new(s);
    q.submit(spec("a", Class::Background, 1), 0).expect("a");
    q.submit(spec("b", Class::Background, 1), 0).expect("b");
    assert!(q.pop(Class::Background, 0).is_some());
    assert!(q.pop(Class::Background, 0).is_none());
    assert_eq!(
        q.counts(Class::Background),
        ClassCounts {
            queued: 1,
            running: 1
        }
    );
}

#[test]
fn backpressure_is_explicit() {
    let mut s = Settings::default();
    s.voice.capacity = 2;
    let mut q = Queue::new(s);
    q.submit(spec("a", Class::Voice, 1), 0).expect("a");
    q.submit(spec("b", Class::Voice, 1), 0).expect("b");
    assert_eq!(
        q.submit(spec("c", Class::Voice, 1), 0),
        Err(TaskqError::Full)
    );
}

#[test]
fn idempotency_key_dedupes() {
    let mut q = queue();
    let mut a = spec("a", Class::Background, 1);
    a.idem_key = Some("same".into());
    let mut b = spec("b", Class::Background, 1);
    b.idem_key = Some("same".into());
    assert_eq!(q.submit(a, 0), Ok(Submitted::Accepted));
    assert_eq!(q.submit(b, 0), Ok(Submitted::Duplicate("a".into())));
}

#[test]
fn duplicate_id_rejected() {
    let mut q = queue();
    q.submit(spec("a", Class::Background, 1), 0).expect("a");
    assert_eq!(
        q.submit(spec("a", Class::Background, 1), 0),
        Err(TaskqError::Invalid)
    );
}

#[test]
fn dependencies_gate_dispatch() {
    let mut q = queue();
    q.submit(spec("a", Class::Background, 1), 0).expect("a");
    let mut b = spec("b", Class::Background, 9);
    b.deps = vec!["a".into()];
    q.submit(b, 0).expect("b");
    assert_eq!(popped(&mut q, Class::Background, 0).as_deref(), Some("a"));
    assert!(q.pop(Class::Background, 0).is_none());
    q.complete("a", vec![], 0).expect("done");
    assert_eq!(popped(&mut q, Class::Background, 0).as_deref(), Some("b"));
}

#[test]
fn unknown_dependency_rejected() {
    let mut q = queue();
    let mut b = spec("b", Class::Background, 1);
    b.deps = vec!["ghost".into()];
    assert_eq!(q.submit(b, 0), Err(TaskqError::UnknownDep));
}

#[test]
fn failed_dependency_cancels_dependents() {
    let mut q = queue();
    q.submit(spec("a", Class::Background, 1), 0).expect("a");
    let mut b = spec("b", Class::Background, 1);
    b.deps = vec!["a".into()];
    q.submit(b, 0).expect("b");
    q.pop(Class::Background, 0).expect("run a");
    q.fail("a", ErrorPayload::new("boom", false), 0)
        .expect("fail");
    assert_eq!(q.state("b").expect("b").state, TaskState::Cancelled);
    let mut c = spec("c", Class::Background, 1);
    c.deps = vec!["a".into()];
    assert_eq!(q.submit(c, 0), Err(TaskqError::DepFailed));
}

#[test]
fn cancelling_parent_cancels_children_and_signals_running() {
    let mut q = queue();
    q.submit(spec("p", Class::Background, 1), 0).expect("p");
    let mut c1 = spec("c1", Class::Background, 1);
    c1.parent = Some("p".into());
    let mut c2 = spec("c2", Class::Background, 1);
    c2.parent = Some("p".into());
    q.submit(c1, 0).expect("c1");
    q.submit(c2, 0).expect("c2");
    q.pop(Class::Background, 0).expect("p");
    q.pop(Class::Background, 0).expect("c1");
    q.complete("p", vec![], 0).expect("p done");
    let signals = q.cancel("c1").expect("cancel");
    assert_eq!(signals, vec!["c1".to_string()]);
    assert_eq!(q.state("c2").expect("c2").state, TaskState::Queued);
}

#[test]
fn parent_failure_cascades() {
    let mut q = queue();
    q.submit(spec("p", Class::Background, 1), 0).expect("p");
    let mut c = spec("c", Class::Background, 1);
    c.parent = Some("p".into());
    q.submit(c, 0).expect("c");
    q.pop(Class::Background, 0).expect("run p");
    q.pop(Class::Background, 0).expect("run c");
    let signals = q
        .fail("p", ErrorPayload::new("boom", false), 0)
        .expect("fail");
    assert_eq!(signals, vec!["c".to_string()]);
    assert_eq!(q.state("c").expect("c").state, TaskState::Cancelled);
}

#[test]
fn transient_failures_retry_with_backoff_then_fail() {
    let mut s = Settings::default();
    s.background.max_retries = 2;
    s.backoff_base_ms = 100;
    let mut q = Queue::new(s);
    q.submit(spec("a", Class::Background, 1), 0).expect("a");
    let mut now = 0;
    for attempt in 1..=2u32 {
        let d = q.pop(Class::Background, now).expect("dispatch");
        assert_eq!(d.attempt, attempt);
        q.fail("a", ErrorPayload::new("net", true), now)
            .expect("fail");
        assert_eq!(q.state("a").expect("a").state, TaskState::Retrying);
        assert!(q.pop(Class::Background, now).is_none());
        let wake = q.next_wake().expect("wake");
        assert!(wake > now);
        now = wake;
    }
    q.pop(Class::Background, now).expect("third");
    q.fail("a", ErrorPayload::new("net", true), now)
        .expect("fail");
    assert_eq!(q.state("a").expect("a").state, TaskState::Failed);
}

#[test]
fn permanent_failure_does_not_retry() {
    let mut q = queue();
    q.submit(spec("a", Class::Background, 1), 0).expect("a");
    q.pop(Class::Background, 0).expect("run");
    q.fail("a", ErrorPayload::new("bad", false), 0)
        .expect("fail");
    assert_eq!(q.state("a").expect("a").state, TaskState::Failed);
}

#[test]
fn backoff_is_capped() {
    let mut s = Settings::default();
    s.background.max_retries = 16;
    s.backoff_base_ms = 1_000;
    s.backoff_cap_ms = 5_000;
    let q = Queue::new(s);
    for attempt in 1..=40 {
        assert!(q.backoff("a", attempt) <= 5_000);
    }
}

#[test]
fn queued_tasks_expire() {
    let mut s = Settings::default();
    s.voice.ttl_ms = 100;
    let mut q = Queue::new(s);
    q.submit(spec("a", Class::Voice, 1), 0).expect("a");
    q.tick(150);
    let e = q.state("a").expect("a");
    assert_eq!(e.state, TaskState::Expired);
    assert_eq!(q.counts(Class::Voice), ClassCounts::default());
}

#[test]
fn terminal_history_is_bounded() {
    let mut s = Settings::default();
    s.retain_terminal = 3;
    let mut q = Queue::new(s);
    for i in 0..10 {
        let id = format!("t{i}");
        q.submit(spec(&id, Class::Background, 1), 0)
            .expect("submit");
        q.pop(Class::Background, 0).expect("run");
        q.complete(&id, vec![], 0).expect("done");
    }
    assert_eq!(q.len(), 3);
}

#[test]
fn complete_requires_running() {
    let mut q = queue();
    q.submit(spec("a", Class::Background, 1), 0).expect("a");
    assert_eq!(q.complete("a", vec![], 0), Err(TaskqError::Terminal));
    assert_eq!(q.complete("zz", vec![], 0), Err(TaskqError::NotFound));
}

#[test]
fn restore_requeues_low_risk_and_fails_high_risk() {
    let mut q = queue();
    q.submit(spec("low", Class::Background, 1), 0).expect("low");
    let mut high = spec("high", Class::Background, 1);
    high.risk_max = Risk::High;
    q.submit(high, 0).expect("high");
    q.submit(spec("waiting", Class::Background, 1), 0)
        .expect("waiting");
    q.pop(Class::Background, 0).expect("run");
    q.pop(Class::Background, 0).expect("run");
    let changes = q.drain();
    let r = Queue::restore(Settings::default(), changes, 5).expect("restore");
    assert_eq!(r.state("low").expect("low").state, TaskState::Queued);
    let high = r.state("high").expect("high");
    assert_eq!(high.state, TaskState::Failed);
    assert_eq!(high.error.expect("err").code, "taskq.interrupted");
    assert_eq!(r.state("waiting").expect("w").state, TaskState::Queued);
}

#[test]
fn restore_rejects_orphan_state() {
    let event = TaskEvent {
        id: "x".into(),
        state: TaskState::Done,
        class: Class::Background,
        attempt: 1,
        progress: 100,
        evidence: vec![],
        error: None,
    };
    let result = Queue::restore(Settings::default(), vec![Change::State { event }], 0);
    assert_eq!(result.err(), Some(TaskqError::Tamper));
}

#[test]
fn spec_validation_fails_closed() {
    let mut s = spec("ok", Class::Voice, 1);
    assert!(s.validate().is_ok());
    s.id = "Bad Id".into();
    assert_eq!(s.validate(), Err(TaskqError::Invalid));
    let mut s = spec("ok", Class::Voice, 1);
    s.budget.wall_ms = 0;
    assert_eq!(s.validate(), Err(TaskqError::Invalid));
    let mut s = spec("ok", Class::Voice, 1);
    s.deps = vec!["ok".into()];
    assert_eq!(s.validate(), Err(TaskqError::Invalid));
    let mut s = spec("ok", Class::Voice, 1);
    s.schema_version = 9;
    assert_eq!(s.validate(), Err(TaskqError::Version));
    let mut s = spec("ok", Class::Voice, 1);
    s.input_ref = "a\u{0}b".into();
    assert_eq!(s.validate(), Err(TaskqError::Invalid));
}

#[test]
fn spec_json_denies_unknown_fields_and_oversize() {
    let ok = spec("ok", Class::Voice, 1).to_json().expect("json");
    assert!(TaskSpec::from_json(&ok).is_ok());
    let extra = ok.replacen('{', "{\"extra\":1,", 1);
    assert_eq!(TaskSpec::from_json(&extra).err(), Some(TaskqError::Parse));
    let big = "x".repeat(Ceilings::PAYLOAD_BYTES + 1);
    assert_eq!(TaskSpec::from_json(&big).err(), Some(TaskqError::TooLarge));
    assert_eq!(
        TaskSpec::from_json("not json").err(),
        Some(TaskqError::Parse)
    );
}

#[test]
fn settings_validation_fails_closed() {
    assert!(Settings::default().validate().is_ok());
    let mut s = Settings::default();
    s.voice.concurrency = 0;
    assert_eq!(s.validate(), Err(TaskqError::Settings));
    let mut s = Settings::default();
    s.background.concurrency = s.background.capacity + 1;
    assert_eq!(s.validate(), Err(TaskqError::Settings));
    let mut s = Settings::default();
    s.backoff_base_ms = s.backoff_cap_ms + 1;
    assert_eq!(s.validate(), Err(TaskqError::Settings));
    let text = serde_json::to_string(&Settings::default()).expect("json");
    assert_eq!(
        Settings::from_json(&text).expect("roundtrip"),
        Settings::default()
    );
    assert!(Settings::from_json("{}").is_err());
}

#[test]
fn error_codes_roundtrip() {
    for code in [
        "taskq.parse",
        "taskq.full",
        "taskq.journal.tamper",
        "taskq.shutdown",
    ] {
        assert_eq!(TaskqError::from_code(code).expect("code").code(), code);
    }
    assert!(TaskqError::from_code("nope").is_none());
}

#[test]
fn randomized_operations_keep_counts_consistent() {
    let mut s = Settings::default();
    s.background.capacity = 64;
    s.background.concurrency = 8;
    s.retain_terminal = 16;
    let mut q = Queue::new(s);
    let mut state = 0x2545_f491_4f6c_dd1du64;
    let mut next = move || {
        state ^= state << 13;
        state ^= state >> 7;
        state ^= state << 17;
        state
    };
    let mut ids: Vec<String> = Vec::new();
    let mut now = 0u64;
    for step in 0..4_000u64 {
        now += next() % 50;
        match next() % 5 {
            0 | 1 => {
                let id = format!("t{step}");
                let mut sp = spec(&id, Class::Background, (next() % 10) as u8);
                if !ids.is_empty() && next() % 3 == 0 {
                    sp.deps = vec![ids[(next() % ids.len() as u64) as usize].clone()];
                }
                if q.submit(sp, now).is_ok() {
                    ids.push(id);
                }
            }
            2 => {
                q.pop(Class::Background, now);
            }
            3 => {
                if let Some(id) = ids.get((next() % (ids.len() as u64 + 1)) as usize).cloned() {
                    let _ = q.complete(&id, vec![], now);
                }
            }
            _ => {
                if let Some(id) = ids.get((next() % (ids.len() as u64 + 1)) as usize).cloned() {
                    if next() % 2 == 0 {
                        let _ = q.fail(&id, ErrorPayload::new("x", next() % 2 == 0), now);
                    } else {
                        let _ = q.cancel(&id);
                    }
                }
            }
        }
        q.tick(now);
        let mut queued = 0;
        let mut running = 0;
        for id in &ids {
            if let Some(e) = q.state(id) {
                match e.state {
                    TaskState::Queued | TaskState::Retrying => queued += 1,
                    TaskState::Running => running += 1,
                    _ => {}
                }
            }
        }
        let c = q.counts(Class::Background);
        assert_eq!((c.queued, c.running), (queued, running), "step {step}");
        assert!(c.running <= 8);
        q.drain();
    }
}
