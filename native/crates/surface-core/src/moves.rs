use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

pub const HOLD_MS: u64 = 30_000;
pub const MAX_TRACKED: usize = 1024;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MoveOrigin {
    User,
    Planner,
}

#[derive(Debug, Clone, Default)]
pub struct MoveGuard {
    placed: BTreeMap<String, (u8, u64)>,
    hold_ms: u64,
}

impl MoveGuard {
    #[must_use]
    pub fn new(hold_ms: u64) -> Self {
        Self {
            placed: BTreeMap::new(),
            hold_ms: hold_ms.max(1000),
        }
    }

    pub fn decide(
        &mut self,
        key: &str,
        wanted: u8,
        origin: MoveOrigin,
        now_ms: u64,
        alive: &[u8],
    ) -> u8 {
        let current = self.placed.get(key).copied();
        let keep = match current {
            Some((screen, since)) if screen != wanted => {
                origin == MoveOrigin::Planner
                    && alive.contains(&screen)
                    && now_ms.saturating_sub(since) < self.hold_ms
            }
            _ => false,
        };
        let chosen = match (keep, current) {
            (true, Some((screen, _))) => screen,
            _ => wanted,
        };
        if current.is_none_or(|(screen, _)| screen != chosen) {
            if self.placed.len() >= MAX_TRACKED && !self.placed.contains_key(key) {
                if let Some(oldest) = self
                    .placed
                    .iter()
                    .min_by_key(|(_, v)| v.1)
                    .map(|(k, _)| k.clone())
                {
                    self.placed.remove(&oldest);
                }
            }
            self.placed.insert(key.to_owned(), (chosen, now_ms));
        }
        chosen
    }

    pub fn forget(&mut self, alive_keys: &[String]) {
        self.placed.retain(|k, _| alive_keys.contains(k));
    }
}
