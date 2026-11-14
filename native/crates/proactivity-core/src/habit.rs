use serde::{Deserialize, Serialize};

use crate::clock::Local;

const SLOTS: usize = 168;
const WEEK: usize = 7;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Habit {
    hits: Vec<u32>,
    stamp: Vec<u64>,
    days: Vec<u32>,
    last_day: u64,
}

impl Default for Habit {
    fn default() -> Self {
        Self::new()
    }
}

fn slot(at: &Local) -> usize {
    at.weekday
        .saturating_mul(24)
        .saturating_add(usize::try_from(at.minute / 60).unwrap_or(0))
}

impl Habit {
    #[must_use]
    pub fn new() -> Self {
        Self {
            hits: vec![0; SLOTS],
            stamp: vec![0; SLOTS],
            days: vec![0; WEEK],
            last_day: 0,
        }
    }

    #[must_use]
    pub fn valid(&self) -> bool {
        self.hits.len() == SLOTS
            && self.stamp.len() == SLOTS
            && self.days.len() == WEEK
            && self.hits.iter().enumerate().all(|(i, h)| {
                self.days
                    .get(i / 24)
                    .is_some_and(|d| *h <= d.saturating_add(1))
            })
    }

    pub fn note_day(&mut self, at: &Local) {
        let marker = at.day.saturating_add(1);
        if self.last_day == marker {
            return;
        }
        if self.last_day != 0 && marker > self.last_day {
            let previous = usize::try_from(self.last_day.saturating_add(2) % 7).unwrap_or(0);
            if let Some(count) = self.days.get_mut(previous) {
                *count = count.saturating_add(1).min(10_000);
            }
        }
        self.last_day = marker;
    }

    pub fn record(&mut self, at: &Local) {
        self.note_day(at);
        let marker = at.day.saturating_add(1);
        let index = slot(at);
        if let (Some(seen), Some(hits)) = (self.stamp.get_mut(index), self.hits.get_mut(index)) {
            if *seen != marker {
                *seen = marker;
                *hits = hits.saturating_add(1);
            }
        }
    }

    #[must_use]
    pub fn probability(&self, at: &Local, min_days: u32) -> Option<u32> {
        let days = *self.days.get(at.weekday)?;
        if days < min_days.max(1) {
            return None;
        }
        let hits = *self.hits.get(slot(at))?;
        let share = u64::from(hits)
            .saturating_mul(1_000)
            .checked_div(u64::from(days))?;
        u32::try_from(share.min(1_000)).ok()
    }
}
