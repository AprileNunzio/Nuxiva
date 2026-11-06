use std::collections::{HashMap, VecDeque};

pub const WINDOW_SECONDS: f64 = 300.0;
pub const MAX_ATTEMPTS: usize = 5;
pub const MAX_TRACKED: usize = 4096;
const MAX_KEY: usize = 64;

#[derive(Debug, Default)]
pub struct LoginLimiter {
    failures: HashMap<String, VecDeque<f64>>,
}

fn key(ip: &str) -> String {
    ip.chars().take(MAX_KEY).collect()
}

impl LoginLimiter {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    fn prune(&mut self, now: f64) {
        self.failures.retain(|_, attempts| {
            attempts.retain(|at| now - at < WINDOW_SECONDS);
            !attempts.is_empty()
        });
    }

    pub fn limited(&mut self, ip: &str, now: f64) -> bool {
        let id = key(ip);
        let Some(attempts) = self.failures.get_mut(&id) else {
            return false;
        };
        attempts.retain(|at| now - at < WINDOW_SECONDS);
        let count = attempts.len();
        if count == 0 {
            self.failures.remove(&id);
        }
        count >= MAX_ATTEMPTS
    }

    pub fn fail(&mut self, ip: &str, now: f64) {
        let id = key(ip);
        if !self.failures.contains_key(&id) && self.failures.len() >= MAX_TRACKED {
            self.prune(now);
            if self.failures.len() >= MAX_TRACKED {
                let oldest = self
                    .failures
                    .iter()
                    .min_by(|a, b| {
                        let left = a.1.back().copied().unwrap_or_default();
                        let right = b.1.back().copied().unwrap_or_default();
                        left.total_cmp(&right)
                    })
                    .map(|(k, _)| k.clone());
                if let Some(oldest) = oldest {
                    self.failures.remove(&oldest);
                }
            }
        }
        let attempts = self.failures.entry(id).or_default();
        attempts.push_back(now);
        while attempts.len() > MAX_ATTEMPTS.saturating_mul(4) {
            attempts.pop_front();
        }
    }

    #[must_use]
    pub fn tracked(&self) -> usize {
        self.failures.len()
    }
}
