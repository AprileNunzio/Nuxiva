use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::error::SentinelError;
use crate::event::Event;
use crate::kind::Group;

const DAY_MS: u64 = 86_400_000;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(transparent)]
pub struct Retention(pub BTreeMap<Group, u16>);

#[must_use]
pub const fn default_days(group: Group) -> u16 {
    match group {
        Group::Appearance => 7,
        Group::GuestAppearance => 1,
        Group::Presence | Group::Guests | Group::Voice | Group::Access | Group::Display => 30,
        Group::Denied | Group::System => 180,
        Group::Automations | Group::Nuxiva | Group::Audit => 90,
    }
}

#[must_use]
pub const fn max_days(group: Group) -> u16 {
    match group {
        Group::Appearance => 30,
        Group::GuestAppearance => 7,
        Group::Denied | Group::System | Group::Audit => 730,
        _ => 365,
    }
}

pub const GROUPS: [Group; 12] = [
    Group::Presence,
    Group::Appearance,
    Group::Guests,
    Group::GuestAppearance,
    Group::Voice,
    Group::Access,
    Group::Denied,
    Group::Automations,
    Group::Nuxiva,
    Group::Display,
    Group::System,
    Group::Audit,
];

impl Default for Retention {
    fn default() -> Self {
        Self(GROUPS.iter().map(|g| (*g, default_days(*g))).collect())
    }
}

impl Retention {
    pub fn with(overrides: &BTreeMap<Group, u16>) -> Result<Self, SentinelError> {
        let mut out = Self::default();
        for (group, days) in overrides {
            if *days == 0 || *days > max_days(*group) {
                return Err(SentinelError::InvalidPolicy);
            }
            out.0.insert(*group, *days);
        }
        Ok(out)
    }

    #[must_use]
    pub fn days(&self, group: Group) -> u16 {
        self.0
            .get(&group)
            .copied()
            .unwrap_or_else(|| default_days(group))
    }

    #[must_use]
    pub fn keeps(&self, event: &Event, now_ms: u64) -> bool {
        let span = u64::from(self.days(event.kind.group())).saturating_mul(DAY_MS);
        now_ms.saturating_sub(event.at_ms) < span
    }

    #[must_use]
    pub fn longest(&self) -> u16 {
        GROUPS.iter().map(|g| self.days(*g)).max().unwrap_or(1)
    }

    #[must_use]
    pub fn day_expired(&self, day_end_ms: u64, now_ms: u64) -> bool {
        now_ms.saturating_sub(day_end_ms) >= u64::from(self.longest()).saturating_mul(DAY_MS)
    }
}
