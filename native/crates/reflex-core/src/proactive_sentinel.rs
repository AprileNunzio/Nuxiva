#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};
use std::sync::atomic::{AtomicU64, Ordering};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ProactiveUrgency {
    Low,
    Medium,
    Critical,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProactiveAdvice {
    pub should_intervene: bool,
    pub urgency: ProactiveUrgency,
    pub semantic_reason: String,
    pub telemetry_metric: String,
    pub measured_value: f32,
    pub suggested_action: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct SentinelSensorySnapshot {
    pub cpu_temp_celsius: f32,
    pub ram_pressure_ratio: f32,
    pub network_threats_blocked: u32,
    pub continuous_session_hours: f32,
    pub hour_of_day: u8,
}

impl Default for SentinelSensorySnapshot {
    fn default() -> Self {
        Self {
            cpu_temp_celsius: 48.0,
            ram_pressure_ratio: 0.40,
            network_threats_blocked: 0,
            continuous_session_hours: 0.5,
            hour_of_day: 14,
        }
    }
}

#[derive(Debug)]
pub struct ProactiveSentinel {
    last_intervention_ms: AtomicU64,
    min_cooldown_ms: u64,
}

impl Default for ProactiveSentinel {
    fn default() -> Self {
        Self::new(300_000) // 5 minutes default cooldown
    }
}

impl ProactiveSentinel {
    #[must_use]
    pub fn new(min_cooldown_ms: u64) -> Self {
        Self {
            last_intervention_ms: AtomicU64::new(0),
            min_cooldown_ms,
        }
    }

    #[must_use]
    pub fn inspect(&self, snapshot: SentinelSensorySnapshot, now_ms: u64) -> ProactiveAdvice {
        let last = self.last_intervention_ms.load(Ordering::Relaxed);
        let elapsed = now_ms.saturating_sub(last);

        // 1. Critical Thermal Alert (bypasses standard cooldown if >= 85°C)
        if snapshot.cpu_temp_celsius >= 85.0 {
            self.last_intervention_ms.store(now_ms, Ordering::Relaxed);
            return ProactiveAdvice {
                should_intervene: true,
                urgency: ProactiveUrgency::Critical,
                semantic_reason: "thermal_alert_critical".to_owned(),
                telemetry_metric: "cpu_temperature_celsius".to_owned(),
                measured_value: snapshot.cpu_temp_celsius,
                suggested_action: Some("governor.boost_fans".to_owned()),
            };
        }

        // Respect cooldown for non-critical proactive remarks
        if elapsed < self.min_cooldown_ms && last > 0 {
            return ProactiveAdvice {
                should_intervene: false,
                urgency: ProactiveUrgency::Low,
                semantic_reason: String::new(),
                telemetry_metric: String::new(),
                measured_value: 0.0,
                suggested_action: None,
            };
        }

        // 2. Network security threat mitigation
        if snapshot.network_threats_blocked > 0 {
            self.last_intervention_ms.store(now_ms, Ordering::Relaxed);
            return ProactiveAdvice {
                should_intervene: true,
                urgency: ProactiveUrgency::Medium,
                semantic_reason: "network_threats_mitigated".to_owned(),
                telemetry_metric: "firewall_blocked_count".to_owned(),
                #[allow(clippy::cast_precision_loss)]
                measured_value: snapshot.network_threats_blocked as f32,
                suggested_action: Some("netguard.audit_log".to_owned()),
            };
        }

        // 3. Late-night fatigue & continuous session awareness
        let is_late = snapshot.hour_of_day >= 23 || snapshot.hour_of_day < 5;
        if is_late && snapshot.continuous_session_hours >= 3.0 {
            self.last_intervention_ms.store(now_ms, Ordering::Relaxed);
            return ProactiveAdvice {
                should_intervene: true,
                urgency: ProactiveUrgency::Low,
                semantic_reason: "fatigue_checkpoint_recommended".to_owned(),
                telemetry_metric: "continuous_session_hours".to_owned(),
                measured_value: snapshot.continuous_session_hours,
                suggested_action: Some("workspace.checkpoint_save".to_owned()),
            };
        }

        ProactiveAdvice {
            should_intervene: false,
            urgency: ProactiveUrgency::Low,
            semantic_reason: String::new(),
            telemetry_metric: String::new(),
            measured_value: 0.0,
            suggested_action: None,
        }
    }
}
