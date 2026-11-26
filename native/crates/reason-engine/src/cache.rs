use std::collections::BTreeMap;

use reason_plan::Plan;
use reason_understand::Goal;

use crate::prompt::goal_shape;

#[derive(Debug, Clone)]
struct Entry {
    plan: Plan,
    expires: u64,
    touched: u64,
}

#[derive(Debug)]
pub struct PlanCache {
    entries: BTreeMap<String, Entry>,
    capacity: usize,
    ttl: u64,
    tick: u64,
    hits: u64,
    misses: u64,
}

#[must_use]
pub fn shape_key(goal: &Goal, generation: u64) -> String {
    let mut hasher = blake3::Hasher::new();
    hasher.update(goal_shape(goal).to_string().as_bytes());
    hasher.update(&[0]);
    hasher.update(&generation.to_le_bytes());
    hasher.finalize().to_hex().to_string()
}

impl PlanCache {
    #[must_use]
    pub fn new(capacity: usize, ttl: u64) -> Self {
        Self {
            entries: BTreeMap::new(),
            capacity: capacity.max(1),
            ttl,
            tick: 0,
            hits: 0,
            misses: 0,
        }
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.entries.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    #[must_use]
    pub fn stats(&self) -> (u64, u64) {
        (self.hits, self.misses)
    }

    pub fn get(&mut self, key: &str, now: u64) -> Option<Plan> {
        self.tick = self.tick.saturating_add(1);
        let tick = self.tick;
        let fresh = self.entries.get(key).is_some_and(|e| e.expires > now);
        if !fresh {
            self.entries.remove(key);
            self.misses = self.misses.saturating_add(1);
            return None;
        }
        let entry = self.entries.get_mut(key)?;
        entry.touched = tick;
        self.hits = self.hits.saturating_add(1);
        Some(entry.plan.clone())
    }

    pub fn put(&mut self, key: String, plan: Plan, now: u64) {
        self.tick = self.tick.saturating_add(1);
        if !self.entries.contains_key(&key) && self.entries.len() >= self.capacity {
            let oldest = self
                .entries
                .iter()
                .min_by_key(|(_, e)| e.touched)
                .map(|(k, _)| k.clone());
            if let Some(oldest) = oldest {
                self.entries.remove(&oldest);
            }
        }
        self.entries.insert(
            key,
            Entry {
                plan,
                expires: now.saturating_add(self.ttl),
                touched: self.tick,
            },
        );
    }

    pub fn forget(&mut self, key: &str) {
        self.entries.remove(key);
    }

    pub fn clear(&mut self) {
        self.entries.clear();
    }
}
