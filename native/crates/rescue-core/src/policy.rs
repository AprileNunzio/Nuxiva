use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::signal::Kind;

pub const MAX_TIERS: u8 = 5;
pub const MAX_ROUNDS: u8 = 5;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "snake_case")]
pub enum Sensitivity {
    Low,
    #[default]
    Normal,
    High,
}

impl Sensitivity {
    #[must_use]
    pub const fn factor(self) -> f64 {
        match self {
            Self::Low => 1.2,
            Self::Normal => 1.0,
            Self::High => 0.75,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Policy {
    pub sensitivity: Sensitivity,
    pub watch: f64,
    pub check: f64,
    pub alert: f64,
    pub critical: f64,
    pub check_in_s: f64,
    pub alert_grace_s: f64,
    pub family_ack_s: f64,
    pub family_tiers: u8,
    pub emergency_repeat_s: f64,
    pub emergency_rounds: u8,
    pub cooldown_s: f64,
    pub reliability: BTreeMap<Kind, f64>,
}

impl Default for Policy {
    fn default() -> Self {
        Self {
            sensitivity: Sensitivity::Normal,
            watch: 0.15,
            check: 0.35,
            alert: 0.7,
            critical: 0.9,
            check_in_s: 30.0,
            alert_grace_s: 12.0,
            family_ack_s: 120.0,
            family_tiers: 2,
            emergency_repeat_s: 180.0,
            emergency_rounds: 3,
            cooldown_s: 300.0,
            reliability: BTreeMap::new(),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PolicyError {
    Thresholds,
    Timing,
    Tiers,
    Reliability,
    Format,
}

impl PolicyError {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Thresholds => "rescue.policy.thresholds",
            Self::Timing => "rescue.policy.timing",
            Self::Tiers => "rescue.policy.tiers",
            Self::Reliability => "rescue.policy.reliability",
            Self::Format => "rescue.policy.format",
        }
    }
}

fn within(value: f64, lo: f64, hi: f64) -> bool {
    value.is_finite() && value >= lo && value <= hi
}

impl Policy {
    pub fn from_json(raw: &str) -> Result<Self, PolicyError> {
        if raw.len() > 16_384 {
            return Err(PolicyError::Format);
        }
        let policy: Self = if raw.trim().is_empty() {
            Self::default()
        } else {
            serde_json::from_str(raw).map_err(|_| PolicyError::Format)?
        };
        policy.validate()?;
        Ok(policy)
    }

    pub fn validate(&self) -> Result<(), PolicyError> {
        let ordered = within(self.watch, 0.02, 0.6)
            && within(self.check, 0.05, 0.8)
            && within(self.alert, 0.1, 0.95)
            && within(self.critical, 0.2, 0.99)
            && self.watch < self.check
            && self.check < self.alert
            && self.alert < self.critical;
        if !ordered {
            return Err(PolicyError::Thresholds);
        }
        let timed = within(self.check_in_s, 10.0, 180.0)
            && within(self.alert_grace_s, 3.0, 60.0)
            && self.alert_grace_s <= self.check_in_s
            && within(self.family_ack_s, 30.0, 900.0)
            && within(self.emergency_repeat_s, 60.0, 1800.0)
            && within(self.cooldown_s, 30.0, 3600.0);
        if !timed {
            return Err(PolicyError::Timing);
        }
        if self.family_tiers == 0
            || self.family_tiers > MAX_TIERS
            || self.emergency_rounds == 0
            || self.emergency_rounds > MAX_ROUNDS
        {
            return Err(PolicyError::Tiers);
        }
        if self.reliability.values().any(|v| !within(*v, 0.05, 1.0)) {
            return Err(PolicyError::Reliability);
        }
        Ok(())
    }

    #[must_use]
    pub fn reliability_of(&self, kind: Kind) -> f64 {
        self.reliability
            .get(&kind)
            .copied()
            .unwrap_or_else(|| kind.reliability())
    }

    fn scaled(&self, value: f64) -> f64 {
        (value * self.sensitivity.factor()).clamp(0.01, 0.99)
    }

    #[must_use]
    pub fn watch_at(&self) -> f64 {
        self.scaled(self.watch)
    }

    #[must_use]
    pub fn check_at(&self) -> f64 {
        self.scaled(self.check)
    }

    #[must_use]
    pub fn alert_at(&self) -> f64 {
        self.scaled(self.alert)
    }

    #[must_use]
    pub fn critical_at(&self) -> f64 {
        self.scaled(self.critical)
    }
}
