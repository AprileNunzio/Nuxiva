use std::collections::HashMap;
use std::sync::{Mutex, PoisonError};
use std::time::Instant;

#[derive(Debug)]
struct Bucket {
    milli: u128,
    at: Instant,
}

#[derive(Debug)]
pub struct RateLimiter {
    per_min: u128,
    max_keys: usize,
    buckets: Mutex<HashMap<String, Bucket>>,
}

const COST: u128 = 1_000;

impl RateLimiter {
    #[must_use]
    pub fn new(per_min: u32, max_keys: usize) -> Self {
        Self {
            per_min: u128::from(per_min),
            max_keys,
            buckets: Mutex::new(HashMap::new()),
        }
    }

    pub fn allow(&self, key: &str, now: Instant) -> bool {
        let capacity = self.per_min.saturating_mul(COST);
        let mut guard = self.buckets.lock().unwrap_or_else(PoisonError::into_inner);
        if !guard.contains_key(key) && guard.len() >= self.max_keys {
            guard.retain(|_, b| now.saturating_duration_since(b.at).as_secs() < 120);
            if guard.len() >= self.max_keys {
                return false;
            }
        }
        let bucket = guard.entry(key.to_owned()).or_insert(Bucket {
            milli: capacity,
            at: now,
        });
        let elapsed = now.saturating_duration_since(bucket.at).as_millis();
        let refill = elapsed
            .saturating_mul(self.per_min)
            .checked_div(60)
            .unwrap_or(0);
        bucket.milli = bucket.milli.saturating_add(refill).min(capacity);
        bucket.at = now;
        if bucket.milli >= COST {
            bucket.milli = bucket.milli.saturating_sub(COST);
            true
        } else {
            false
        }
    }
}
