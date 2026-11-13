use std::time::{Duration, Instant};

use crate::{Backoff, Breaker, Settings};

fn settings() -> Settings {
    Settings {
        backoff_base_ms: 100,
        backoff_max_ms: 1_000,
        backoff_jitter_pct: 0,
        breaker_failures: 3,
        breaker_window_ms: 500,
        ..Settings::default()
    }
}

#[test]
fn delays_double_up_to_the_cap_and_reset() {
    let mut backoff = Backoff::new(&settings());
    let delays: Vec<u128> = (0..6).map(|_| backoff.next(0).as_millis()).collect();
    assert_eq!(delays, [100, 200, 400, 800, 1_000, 1_000]);
    assert_eq!(backoff.attempts(), 6);
    backoff.reset();
    assert_eq!(backoff.next(0), Duration::from_millis(100));
}

#[test]
fn jitter_stays_within_bounds() {
    let jittered = Settings {
        backoff_jitter_pct: 20,
        ..settings()
    };
    for entropy in 0..200u64 {
        let mut backoff = Backoff::new(&jittered);
        let ms = backoff.next(entropy).as_millis();
        assert!((80..=120).contains(&ms), "{ms}");
    }
}

#[test]
fn huge_attempt_counts_do_not_overflow() {
    let mut backoff = Backoff::new(&settings());
    for _ in 0..200 {
        assert!(backoff.next(u64::MAX) <= Duration::from_millis(1_000));
    }
}

#[test]
fn breaker_opens_after_threshold_and_forgets_old_failures() {
    let mut breaker = Breaker::new(&settings());
    let start = Instant::now();
    breaker.failure(start);
    breaker.failure(start);
    assert!(!breaker.open(start));
    breaker.failure(start);
    assert!(breaker.open(start));
    let later = start + Duration::from_millis(600);
    assert!(!breaker.open(later));
    breaker.failure(later);
    breaker.success();
    assert!(!breaker.open(later));
}
