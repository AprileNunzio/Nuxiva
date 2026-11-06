use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::error::MemoryError;
use crate::sighting::Audience;
use crate::store::Header;

pub const PINNED_DAYS: u16 = 365;
pub const AUDIENCES: [Audience; 4] = [
    Audience::Household,
    Audience::Guest,
    Audience::Passerby,
    Audience::Object,
];

#[must_use]
pub const fn default_days(a: Audience) -> u16 {
    match a {
        Audience::Household | Audience::Object => 30,
        Audience::Guest | Audience::Passerby => 1,
    }
}

#[must_use]
pub const fn max_days(a: Audience) -> u16 {
    match a {
        Audience::Household | Audience::Object => 365,
        Audience::Guest | Audience::Passerby => 7,
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(transparent)]
pub struct Policy(pub BTreeMap<Audience, u16>);

impl Default for Policy {
    fn default() -> Self {
        Self(AUDIENCES.iter().map(|a| (*a, default_days(*a))).collect())
    }
}

impl Policy {
    pub fn with(overrides: &BTreeMap<Audience, u16>) -> Result<Self, MemoryError> {
        let mut out = Self::default();
        for (a, days) in overrides {
            if *days == 0 || *days > max_days(*a) {
                return Err(MemoryError::InvalidPolicy);
            }
            out.0.insert(*a, *days);
        }
        Ok(out)
    }

    #[must_use]
    pub fn days(&self, a: Audience) -> u16 {
        self.0.get(&a).copied().unwrap_or_else(|| default_days(a))
    }

    #[must_use]
    pub fn keeps(&self, header: &Header, age_days: u16) -> bool {
        let limit = if header.pinned {
            PINNED_DAYS
        } else {
            self.days(header.audience)
        };
        age_days < limit
    }

    #[must_use]
    pub fn day_expired(&self, age_days: u16) -> bool {
        age_days >= PINNED_DAYS
    }
}
