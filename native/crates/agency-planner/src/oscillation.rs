use std::collections::HashMap;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum OscillationVerdict {
    Permitted { attempt: usize },
    OscillationDetected { failures: usize, max_allowed: usize },
}

#[derive(Debug, Clone)]
pub struct AntiOscillationGuard {
    failure_counts: HashMap<String, usize>,
    max_consecutive_failures: usize,
}

impl AntiOscillationGuard {
    #[must_use]
    pub fn new(max_consecutive_failures: usize) -> Self {
        Self {
            failure_counts: HashMap::new(),
            max_consecutive_failures,
        }
    }

    pub fn record_failure(&mut self, task_key: &str) -> OscillationVerdict {
        let count = self.failure_counts.entry(task_key.to_string()).or_insert(0);
        *count = count.saturating_add(1);
        if *count >= self.max_consecutive_failures {
            OscillationVerdict::OscillationDetected {
                failures: *count,
                max_allowed: self.max_consecutive_failures,
            }
        } else {
            OscillationVerdict::Permitted { attempt: *count }
        }
    }

    pub fn reset(&mut self, task_key: &str) {
        self.failure_counts.remove(task_key);
    }

    #[must_use]
    pub fn failure_count(&self, task_key: &str) -> usize {
        self.failure_counts.get(task_key).copied().unwrap_or(0)
    }
}
