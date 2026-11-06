use crate::{Action, LoopBook, Outcome, Policy};

const POLICY: Policy = Policy {
    restart_enabled: true,
    backoff_min: 1.0,
    backoff_max: 8.0,
    stable_after: 120.0,
    report_every: 10,
};

fn near(a: f64, b: f64) -> bool {
    (a - b).abs() < 1e-9
}

#[test]
fn backoff_doubles_caps_and_resets_after_stable_run() {
    let mut book = LoopBook::new();
    assert!(book.add("radio", 0.0, 0.0));
    let mut delays = Vec::new();
    let mut now = 0.0;
    for _ in 0..6 {
        book.start("radio", now);
        now += 1.0;
        let decision = book.exit("radio", Outcome::Failed, "Boom", now, POLICY);
        delays.push(decision.map_or(-1.0, |d| d.delay));
    }
    for (got, want) in delays.iter().zip([1.0, 2.0, 4.0, 8.0, 8.0, 8.0]) {
        assert!(near(*got, want));
    }
    book.start("radio", now);
    let decision = book.exit("radio", Outcome::Failed, "Boom", now + 500.0, POLICY);
    assert!(decision.is_some_and(|d| near(d.delay, 1.0) && d.action == Action::Restart));
}

#[test]
fn reports_first_and_every_tenth_restart() {
    let mut book = LoopBook::new();
    book.add("x", 0.0, 0.0);
    let mut reports = Vec::new();
    for i in 0..20 {
        book.start("x", f64::from(i));
        let d = book.exit("x", Outcome::Cancelled, "bloccato", f64::from(i), POLICY);
        reports.push(d.is_some_and(|d| d.report));
    }
    let flagged: Vec<usize> = reports
        .iter()
        .enumerate()
        .filter(|(_, r)| **r)
        .map(|(i, _)| i + 1)
        .collect();
    assert_eq!(flagged, vec![1, 10, 20]);
}

#[test]
fn finish_and_halt() {
    let mut book = LoopBook::new();
    book.add("a", 0.0, 0.0);
    book.start("a", 0.0);
    assert!(
        book.exit("a", Outcome::Done, "", 1.0, POLICY)
            .is_some_and(|d| d.action == Action::Finish)
    );
    let off = Policy {
        restart_enabled: false,
        ..POLICY
    };
    book.start("a", 2.0);
    assert!(
        book.exit("a", Outcome::Failed, "E", 3.0, off)
            .is_some_and(|d| d.action == Action::Halt && d.report)
    );
    let view = book.snapshot(4.0);
    assert_eq!(view.first().map(|v| v.state), Some("halted"));
    assert!(
        book.exit("missing", Outcome::Done, "", 0.0, POLICY)
            .is_none()
    );
}

#[test]
fn stalls_are_detected_once_per_window() {
    let mut book = LoopBook::new();
    book.add("tick", 2.0, 0.0);
    book.add("once", 0.0, 0.0);
    book.start("tick", 0.0);
    book.start("once", 0.0);
    assert!(book.stalled(5.0, 5.0).is_empty());
    assert_eq!(book.stalled(11.0, 5.0), vec!["tick".to_owned()]);
    assert!(book.stalled(12.0, 5.0).is_empty());
    book.beat("tick", 20.0);
    assert!(book.stalled(25.0, 5.0).is_empty());
    let totals = book.totals();
    assert_eq!((totals.loops, totals.running, totals.stalls), (2, 2, 1));
}

#[test]
fn limits_and_bad_numbers() {
    let mut book = LoopBook::new();
    assert!(!book.add("", 0.0, 0.0));
    for i in 0..300 {
        book.add(&format!("l{i}"), f64::NAN, 0.0);
    }
    assert_eq!(book.totals().loops, crate::MAX_LOOPS);
    let weird = Policy {
        backoff_min: f64::NAN,
        backoff_max: -1.0,
        report_every: 0,
        ..POLICY
    };
    book.start("l0", 0.0);
    assert!(
        book.exit("l0", Outcome::Failed, &"e".repeat(500), 0.0, weird)
            .is_some_and(|d| d.delay.is_finite())
    );
    assert_eq!(
        book.snapshot(0.0).first().map(|v| v.last_error.len()),
        Some(crate::MAX_REASON)
    );
}
