use std::collections::VecDeque;
use std::time::{Duration, Instant};

use crate::settings::Settings;

#[derive(Debug, Clone)]
pub struct Backoff {
    base_ms: u64,
    max_ms: u64,
    jitter_pct: u64,
    attempt: u32,
}

fn to_u64(value: usize) -> u64 {
    u64::try_from(value).unwrap_or(u64::MAX)
}

impl Backoff {
    #[must_use]
    pub fn new(settings: &Settings) -> Self {
        Self {
            base_ms: to_u64(settings.backoff_base_ms),
            max_ms: to_u64(settings.backoff_max_ms),
            jitter_pct: to_u64(settings.backoff_jitter_pct),
            attempt: 0,
        }
    }

    pub fn next(&mut self, entropy: u64) -> Duration {
        let factor = 1u64.checked_shl(self.attempt.min(40)).unwrap_or(u64::MAX);
        let raw = self.base_ms.saturating_mul(factor).min(self.max_ms);
        self.attempt = self.attempt.saturating_add(1);
        let spread = self.jitter_pct.saturating_mul(2).saturating_add(1);
        let offset = entropy.checked_rem(spread).unwrap_or(0);
        let percent = 100u64
            .saturating_sub(self.jitter_pct)
            .saturating_add(offset);
        let jittered = raw.saturating_mul(percent).checked_div(100).unwrap_or(raw);
        Duration::from_millis(jittered.min(self.max_ms.max(raw)))
    }

    pub fn reset(&mut self) {
        self.attempt = 0;
    }

    #[must_use]
    pub fn attempts(&self) -> u32 {
        self.attempt
    }
}

#[derive(Debug, Clone)]
pub struct Breaker {
    threshold: usize,
    window: Duration,
    failures: VecDeque<Instant>,
}

impl Breaker {
    #[must_use]
    pub fn new(settings: &Settings) -> Self {
        Self {
            threshold: settings.breaker_failures,
            window: Duration::from_millis(to_u64(settings.breaker_window_ms)),
            failures: VecDeque::new(),
        }
    }

    pub fn failure(&mut self, now: Instant) {
        self.failures.push_back(now);
        self.trim(now);
    }

    pub fn success(&mut self) {
        self.failures.clear();
    }

    fn trim(&mut self, now: Instant) {
        while self
            .failures
            .front()
            .is_some_and(|at| now.saturating_duration_since(*at) > self.window)
        {
            self.failures.pop_front();
        }
    }

    #[must_use]
    pub fn open(&mut self, now: Instant) -> bool {
        self.trim(now);
        self.failures.len() >= self.threshold
    }
}
