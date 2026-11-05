use crate::memory::{MemorySample, MemoryState};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum HealthStatus {
    Healthy,
    Degraded,
    Critical,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SystemStatus {
    pub uptime_seconds: f64,
    pub health: HealthStatus,
    pub memory_state: MemoryState,
    pub memory_percent: f64,
    pub active_processes_count: usize,
    pub notifications_count: usize,
    pub throttled: bool,
}

#[must_use]
pub fn calculate_system_status(
    uptime_seconds: f64,
    memory_sample: &MemorySample,
    active_processes_count: usize,
    notifications_count: usize,
) -> SystemStatus {
    let health = match memory_sample.state {
        MemoryState::Critical => HealthStatus::Critical,
        MemoryState::Warning => HealthStatus::Degraded,
        MemoryState::Normal => {
            if memory_sample.throttled {
                HealthStatus::Degraded
            } else {
                HealthStatus::Healthy
            }
        }
    };

    SystemStatus {
        uptime_seconds,
        health,
        memory_state: memory_sample.state,
        memory_percent: memory_sample.percent,
        active_processes_count,
        notifications_count,
        throttled: memory_sample.throttled,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn healthy_status_calculation() {
        let mem = MemorySample {
            total_bytes: 1000,
            available_bytes: 600,
            used_bytes: 400,
            percent: 40.0,
            state: MemoryState::Normal,
            throttled: false,
        };

        let status = calculate_system_status(120.5, &mem, 5, 0);
        assert_eq!(status.health, HealthStatus::Healthy);
        assert_eq!(status.active_processes_count, 5);
        assert!(!status.throttled);
    }

    #[test]
    fn degraded_and_critical_status() {
        let warning_mem = MemorySample {
            total_bytes: 1000,
            available_bytes: 150,
            used_bytes: 850,
            percent: 85.0,
            state: MemoryState::Warning,
            throttled: false,
        };
        let status = calculate_system_status(300.0, &warning_mem, 10, 2);
        assert_eq!(status.health, HealthStatus::Degraded);

        let crit_mem = MemorySample {
            total_bytes: 1000,
            available_bytes: 50,
            used_bytes: 950,
            percent: 95.0,
            state: MemoryState::Critical,
            throttled: true,
        };
        let status_crit = calculate_system_status(400.0, &crit_mem, 12, 5);
        assert_eq!(status_crit.health, HealthStatus::Critical);
        assert!(status_crit.throttled);
    }
}
