use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum MemoryState {
    Normal,
    Warning,
    Critical,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MemorySample {
    pub total_bytes: u64,
    pub available_bytes: u64,
    pub used_bytes: u64,
    pub percent: f64,
    pub state: MemoryState,
    pub throttled: bool,
}

#[derive(Debug, Clone)]
pub struct MemoryManager {
    warning_percent: f64,
    critical_percent: f64,
    critical_min_available_bytes: u64,
    warning_consecutive_threshold: u32,
    warning_count: u32,
}

impl Default for MemoryManager {
    fn default() -> Self {
        Self {
            warning_percent: 80.0,
            critical_percent: 90.0,
            critical_min_available_bytes: 268_435_456,
            warning_consecutive_threshold: 3,
            warning_count: 0,
        }
    }
}

impl MemoryManager {
    #[must_use]
    pub const fn new(
        warning_percent: f64,
        critical_percent: f64,
        critical_min_available_bytes: u64,
        warning_consecutive_threshold: u32,
    ) -> Self {
        Self {
            warning_percent,
            critical_percent,
            critical_min_available_bytes,
            warning_consecutive_threshold,
            warning_count: 0,
        }
    }

    #[must_use]
    #[allow(clippy::cast_precision_loss)]
    pub fn evaluate(&mut self, total_bytes: u64, available_bytes: u64) -> MemorySample {
        let safe_available = if available_bytes > total_bytes {
            total_bytes
        } else {
            available_bytes
        };
        let used_bytes = total_bytes.saturating_sub(safe_available);
        let percent = if total_bytes == 0 {
            0.0
        } else {
            let ratio = (used_bytes as f64) / (total_bytes as f64);
            (ratio * 1000.0).round() / 10.0
        };

        let state = if percent >= self.critical_percent
            || safe_available <= self.critical_min_available_bytes
        {
            MemoryState::Critical
        } else if percent >= self.warning_percent {
            MemoryState::Warning
        } else {
            MemoryState::Normal
        };

        match state {
            MemoryState::Critical => {
                self.warning_count = self.warning_consecutive_threshold;
            }
            MemoryState::Warning => {
                self.warning_count = self.warning_count.saturating_add(1);
            }
            MemoryState::Normal => {
                self.warning_count = 0;
            }
        }

        let throttled = match state {
            MemoryState::Critical => true,
            MemoryState::Warning => self.warning_count >= self.warning_consecutive_threshold,
            MemoryState::Normal => false,
        };

        MemorySample {
            total_bytes,
            available_bytes: safe_available,
            used_bytes,
            percent,
            state,
            throttled,
        }
    }

    #[must_use]
    pub const fn is_throttled(&self) -> bool {
        self.warning_count >= self.warning_consecutive_threshold
    }

    pub fn reset(&mut self) {
        self.warning_count = 0;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normal_memory_evaluation() {
        let mut mgr = MemoryManager::default();
        let sample = mgr.evaluate(16_000_000_000, 8_000_000_000);
        assert_eq!(sample.state, MemoryState::Normal);
        assert!(!sample.throttled);
        assert!((sample.percent - 50.0).abs() < f64::EPSILON);
    }

    #[test]
    fn warning_and_throttle_escalation() {
        let mut mgr = MemoryManager::default();
        let total = 10_000_000_000;
        let available = 1_500_000_000;

        let s1 = mgr.evaluate(total, available);
        assert_eq!(s1.state, MemoryState::Warning);
        assert!(!s1.throttled);

        let s2 = mgr.evaluate(total, available);
        assert_eq!(s2.state, MemoryState::Warning);
        assert!(!s2.throttled);

        let s3 = mgr.evaluate(total, available);
        assert_eq!(s3.state, MemoryState::Warning);
        assert!(s3.throttled);
    }

    #[test]
    fn critical_memory_triggers_immediate_throttling() {
        let mut mgr = MemoryManager::default();
        let sample = mgr.evaluate(10_000_000_000, 100_000_000);
        assert_eq!(sample.state, MemoryState::Critical);
        assert!(sample.throttled);
    }

    #[test]
    fn zero_total_handled_safely() {
        let mut mgr = MemoryManager::default();
        let sample = mgr.evaluate(0, 0);
        assert!(sample.percent.abs() < f64::EPSILON);
        assert_eq!(sample.state, MemoryState::Critical);
    }
}
