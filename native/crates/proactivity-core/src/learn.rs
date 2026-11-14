use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

const DECAY_AT: u32 = 64;
const FADE_MS: u64 = 14 * 86_400_000;
const MIN_MULT: u32 = 250;
const MAX_MULT: u32 = 1_250;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Feedback {
    Accepted,
    Refused,
    Undone,
    Ignored,
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Record {
    pos: u32,
    neg: u32,
    undone: u32,
    ignored: u32,
    muted_until: u64,
    touched: u64,
}

impl Record {
    fn posterior(&self) -> u32 {
        let total = self.pos.saturating_add(self.neg).saturating_add(8);
        let share = u64::from(self.pos.saturating_add(4))
            .saturating_mul(1_000)
            .checked_div(u64::from(total))
            .unwrap_or(500);
        u32::try_from(share).unwrap_or(500)
    }

    fn faded(&self, now: u64) -> Self {
        let shift = u32::try_from((now.saturating_sub(self.touched) / FADE_MS).min(8)).unwrap_or(8);
        Self {
            pos: self.pos >> shift,
            neg: self.neg >> shift,
            ..*self
        }
    }

    fn multiplier(&self) -> u32 {
        self.posterior().saturating_mul(2).clamp(MIN_MULT, MAX_MULT)
    }

    fn decay(&mut self) {
        if self.pos.saturating_add(self.neg) > DECAY_AT {
            self.pos = self.pos.saturating_mul(3) / 4;
            self.neg = self.neg.saturating_mul(3) / 4;
        }
    }
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(transparent)]
pub struct Learner {
    records: BTreeMap<String, Record>,
}

#[must_use]
pub fn key(rule: &str, person: Option<&str>) -> String {
    format!("{rule}|{}", person.unwrap_or(""))
}

impl Learner {
    #[must_use]
    pub fn multiplier(&self, key: &str, now: u64) -> u32 {
        self.records
            .get(key)
            .map_or(1_000, |r| r.faded(now).multiplier())
    }

    #[must_use]
    pub fn muted(&self, key: &str, now: u64) -> bool {
        self.records.get(key).is_some_and(|r| r.muted_until > now)
    }

    #[must_use]
    pub fn demotions(&self, key: &str) -> u32 {
        self.records.get(key).map_or(0, |r| r.undone / 2)
    }

    pub fn feedback(&mut self, key: &str, kind: Feedback, now: u64, mute_ms: u64) {
        if !self.records.contains_key(key) && self.records.len() >= 8_192 {
            return;
        }
        let record = self.records.entry(key.to_owned()).or_default();
        *record = record.faded(now);
        record.touched = now;
        match kind {
            Feedback::Accepted => {
                record.pos = record.pos.saturating_add(1);
                record.undone = record.undone.saturating_sub(1);
            }
            Feedback::Refused => record.neg = record.neg.saturating_add(1),
            Feedback::Undone => {
                record.neg = record.neg.saturating_add(2);
                record.undone = record.undone.saturating_add(1);
            }
            Feedback::Ignored => {
                record.ignored = record.ignored.saturating_add(1);
                if record.ignored >= 3 {
                    record.ignored = 0;
                    record.neg = record.neg.saturating_add(1);
                }
            }
        }
        record.decay();
        if record.neg >= 5 && record.posterior() <= 300 {
            record.muted_until = now.saturating_add(mute_ms);
        }
    }

    #[must_use]
    pub fn valid(&self) -> bool {
        self.records.len() <= 8_192
            && self
                .records
                .iter()
                .all(|(k, r)| k.len() <= 160 && r.pos <= 1_000_000 && r.neg <= 1_000_000)
    }

    pub fn clear_mute(&mut self, key: &str) {
        if let Some(record) = self.records.get_mut(key) {
            *record = Record::default();
        }
    }
}
