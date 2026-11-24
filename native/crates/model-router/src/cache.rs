use std::collections::BTreeMap;

use crate::profile::{Sensitivity, Task};

#[derive(Debug, Clone, PartialEq, Eq)]
struct Entry {
    answer: String,
    expires: u64,
    touched: u64,
}

#[derive(Debug)]
pub struct Cache {
    entries: BTreeMap<String, Entry>,
    capacity: usize,
    ttl: u64,
    tick: u64,
}

#[must_use]
pub fn cache_key(task: Task, model: &str, prompt: &str) -> String {
    let normalized: String = prompt.split_whitespace().collect::<Vec<_>>().join(" ");
    let mut hasher = blake3::Hasher::new();
    hasher.update(format!("{task:?}").as_bytes());
    hasher.update(&[0]);
    hasher.update(model.as_bytes());
    hasher.update(&[0]);
    hasher.update(normalized.as_bytes());
    hasher.finalize().to_hex().to_string()
}

impl Cache {
    #[must_use]
    pub fn new(capacity: usize, ttl: u64) -> Self {
        Self {
            entries: BTreeMap::new(),
            capacity,
            ttl,
            tick: 0,
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

    pub fn get(&mut self, key: &str, now: u64) -> Option<String> {
        self.tick = self.tick.saturating_add(1);
        let tick = self.tick;
        let entry = self.entries.get_mut(key)?;
        if entry.expires <= now {
            self.entries.remove(key);
            return None;
        }
        entry.touched = tick;
        Some(entry.answer.clone())
    }

    pub fn put(&mut self, key: String, answer: String, sensitivity: Sensitivity, now: u64) {
        if sensitivity >= Sensitivity::Private || self.capacity == 0 {
            return;
        }
        self.tick = self.tick.saturating_add(1);
        if self.entries.len() >= self.capacity && !self.entries.contains_key(&key) {
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
                answer,
                expires: now.saturating_add(self.ttl),
                touched: self.tick,
            },
        );
    }
}
