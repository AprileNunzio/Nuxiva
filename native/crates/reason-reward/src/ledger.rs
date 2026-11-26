use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::error::{RewardError, RewardResult};
use crate::reward::{GAIN_MAX, Reward};

pub const MAX_KEYS: usize = 4_096;
pub const MAX_LEDGER_BYTES: usize = 2 * 1024 * 1024;
pub const WINDOW: u32 = 256;
const PRIOR_GAIN: u64 = 5_000;
const PRIOR_WEIGHT: u64 = 4;
const MARGIN: u64 = 5_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Subject {
    Model,
    Capability,
    Agent,
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Key {
    pub subject: Subject,
    pub id: String,
    pub task: String,
}

fn valid_name(value: &str, extra: &[u8]) -> bool {
    !value.is_empty()
        && value.len() <= 64
        && value.bytes().all(|b| {
            b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_' || extra.contains(&b)
        })
}

impl Key {
    pub fn new(subject: Subject, id: &str, task: &str) -> RewardResult<Self> {
        let key = Self {
            subject,
            id: id.to_owned(),
            task: task.to_owned(),
        };
        key.validate()?;
        Ok(key)
    }

    pub fn validate(&self) -> RewardResult<()> {
        if !valid_name(&self.id, b".-:/") || !valid_name(&self.task, b"") {
            return Err(RewardError::Invalid("key"));
        }
        Ok(())
    }
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Tally {
    pub trials: u32,
    pub gain_sum: u64,
    pub unsafe_count: u32,
}

impl Tally {
    fn validate(&self) -> RewardResult<()> {
        let ceiling = u64::from(self.trials).saturating_mul(u64::from(GAIN_MAX));
        if self.trials > WINDOW || self.gain_sum > ceiling || self.unsafe_count > self.trials {
            return Err(RewardError::Invalid("tally"));
        }
        Ok(())
    }

    fn record(&mut self, reward: &Reward) {
        if self.trials >= WINDOW {
            self.trials /= 2;
            self.gain_sum /= 2;
            self.unsafe_count /= 2;
        }
        self.trials = self.trials.saturating_add(1);
        self.gain_sum = self.gain_sum.saturating_add(u64::from(reward.gain()));
        self.unsafe_count = self
            .unsafe_count
            .saturating_add(u32::from(reward.unsafe_action));
    }

    #[must_use]
    pub fn estimate_bps(&self) -> u16 {
        let weight = u64::from(self.trials).saturating_add(PRIOR_WEIGHT);
        let mass = self
            .gain_sum
            .saturating_add(PRIOR_GAIN.saturating_mul(PRIOR_WEIGHT));
        u16::try_from(
            mass.checked_div(weight)
                .unwrap_or(0)
                .min(u64::from(GAIN_MAX)),
        )
        .unwrap_or(0)
    }

    #[must_use]
    pub fn lower_bound_bps(&self) -> u16 {
        let spread = MARGIN
            .checked_div(u64::from(self.trials).saturating_add(1).isqrt())
            .unwrap_or(MARGIN);
        let spread = u16::try_from(spread).unwrap_or(u16::MAX);
        self.estimate_bps().saturating_sub(spread)
    }

    #[must_use]
    pub fn unsafe_per_mille(&self) -> u32 {
        let scaled = u64::from(self.unsafe_count)
            .saturating_mul(1_000)
            .checked_div(u64::from(self.trials))
            .unwrap_or(0);
        u32::try_from(scaled).unwrap_or(u32::MAX)
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Entry {
    key: Key,
    tally: Tally,
}

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Ledger {
    tallies: BTreeMap<Key, Tally>,
}

impl Ledger {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    pub fn record(&mut self, key: &Key, reward: &Reward) -> RewardResult<()> {
        key.validate()?;
        if !reward.verified {
            return Ok(());
        }
        if !self.tallies.contains_key(key) && self.tallies.len() >= MAX_KEYS {
            return Err(RewardError::Full);
        }
        self.tallies.entry(key.clone()).or_default().record(reward);
        Ok(())
    }

    #[must_use]
    pub fn get(&self, key: &Key) -> Option<&Tally> {
        self.tallies.get(key)
    }

    pub fn iter(&self) -> impl Iterator<Item = (&Key, &Tally)> {
        self.tallies.iter()
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.tallies.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.tallies.is_empty()
    }

    pub fn forget(&mut self, key: &Key) -> bool {
        self.tallies.remove(key).is_some()
    }

    pub fn to_json(&self) -> RewardResult<String> {
        let entries: Vec<Entry> = self
            .tallies
            .iter()
            .map(|(key, tally)| Entry {
                key: key.clone(),
                tally: *tally,
            })
            .collect();
        Ok(serde_json::to_string(&entries)?)
    }

    pub fn from_json(bytes: &[u8]) -> RewardResult<Self> {
        if bytes.len() > MAX_LEDGER_BYTES {
            return Err(RewardError::Invalid("size"));
        }
        let entries: Vec<Entry> = serde_json::from_slice(bytes)?;
        if entries.len() > MAX_KEYS {
            return Err(RewardError::Full);
        }
        let mut tallies = BTreeMap::new();
        for entry in entries {
            entry.key.validate()?;
            entry.tally.validate()?;
            if tallies.insert(entry.key, entry.tally).is_some() {
                return Err(RewardError::Invalid("duplicate"));
            }
        }
        Ok(Self { tallies })
    }
}
