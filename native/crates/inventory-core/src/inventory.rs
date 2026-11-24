use std::collections::BTreeMap;

use crate::audit::{Chain, Entry};
use crate::error::{InventoryError, InventoryResult};
use crate::model::{Diff, Found, Item, Kind, Origin, Snapshot, State};
use crate::scanner::Scanner;

pub const DEFAULT_GRACE_MS: u64 = 10_000;

#[derive(Debug, Clone)]
pub struct Inventory {
    items: BTreeMap<(Kind, String), Item>,
    generation: u64,
    grace_ms: u64,
    audit: Chain,
}

impl Default for Inventory {
    fn default() -> Self {
        Self::new(DEFAULT_GRACE_MS)
    }
}

impl Inventory {
    #[must_use]
    pub fn new(grace_ms: u64) -> Self {
        Self {
            items: BTreeMap::new(),
            generation: 0,
            grace_ms,
            audit: Chain::default(),
        }
    }

    #[must_use]
    pub fn generation(&self) -> u64 {
        self.generation
    }

    #[must_use]
    pub fn audit(&self) -> &[Entry] {
        self.audit.entries()
    }

    #[must_use]
    pub fn get(&self, kind: Kind, id: &str) -> Option<&Item> {
        self.items.get(&(kind, id.to_owned()))
    }

    #[must_use]
    pub fn count(&self, kind: Kind) -> usize {
        self.items.keys().filter(|(k, _)| *k == kind).count()
    }

    #[must_use]
    pub fn snapshot(&self) -> Snapshot {
        Snapshot {
            generation: self.generation,
            items: self.items.values().cloned().collect(),
        }
    }

    pub fn scan(&mut self, scanner: &dyn Scanner, now_ms: u64) -> InventoryResult<Diff> {
        let found = scanner.scan()?;
        Ok(self.apply(scanner.kind(), &found, now_ms))
    }

    pub fn apply(&mut self, kind: Kind, found: &[Found], now_ms: u64) -> Diff {
        let mut diff = Diff::default();
        let mut seen = std::collections::BTreeSet::new();
        for entry in found {
            if !seen.insert(entry.id.as_str()) {
                diff.rejected.push(entry.id.clone());
                continue;
            }
            let key = (kind, entry.id.clone());
            match self.items.get_mut(&key) {
                None => {
                    let trusted = entry.origin == Origin::System;
                    self.items.insert(
                        key,
                        Item {
                            kind,
                            id: entry.id.clone(),
                            origin: entry.origin,
                            hash: entry.hash,
                            state: if trusted {
                                State::Active
                            } else {
                                State::Degraded
                            },
                            first_seen_ms: now_ms,
                            last_seen_ms: now_ms,
                            verified: trusted,
                        },
                    );
                    diff.added.push(entry.id.clone());
                }
                Some(item) if item.state == State::Revoked => {
                    item.last_seen_ms = now_ms;
                }
                Some(item) if item.origin == Origin::System && entry.origin != Origin::System => {
                    diff.rejected.push(entry.id.clone());
                }
                Some(item) => {
                    item.last_seen_ms = now_ms;
                    if item.hash != entry.hash {
                        item.hash = entry.hash;
                        item.verified = item.origin == Origin::System;
                        if item.origin != Origin::System {
                            item.state = State::Degraded;
                        }
                        diff.changed.push(entry.id.clone());
                    } else if item.state == State::Degraded && item.verified {
                        item.state = State::Active;
                        diff.changed.push(entry.id.clone());
                    }
                }
            }
        }
        for ((item_kind, id), item) in &mut self.items {
            if *item_kind != kind || seen.contains(id.as_str()) || item.state == State::Revoked {
                continue;
            }
            let absent = now_ms.saturating_sub(item.last_seen_ms);
            if absent >= self.grace_ms {
                item.state = State::Revoked;
                diff.revoked.push(id.clone());
            } else if item.state == State::Active {
                item.state = State::Degraded;
                diff.missing.push(id.clone());
            }
        }
        self.record(&diff, kind, now_ms);
        diff
    }

    fn record(&mut self, diff: &Diff, kind: Kind, now_ms: u64) {
        if diff.is_empty() && diff.rejected.is_empty() {
            return;
        }
        self.generation = self.generation.saturating_add(1);
        let event = format!(
            "gen={} kind={kind:?} added={} changed={} missing={} revoked={} rejected={}",
            self.generation,
            diff.added.join(","),
            diff.changed.join(","),
            diff.missing.join(","),
            diff.revoked.join(","),
            diff.rejected.join(",")
        );
        self.audit.append(now_ms, event);
    }

    pub fn verify(&mut self, kind: Kind, id: &str, now_ms: u64) -> InventoryResult<()> {
        let item = self
            .items
            .get_mut(&(kind, id.to_owned()))
            .ok_or_else(|| InventoryError::Unknown(id.to_owned()))?;
        if item.state == State::Revoked {
            return Err(InventoryError::Invalid("revoked"));
        }
        item.verified = true;
        item.state = State::Active;
        self.generation = self.generation.saturating_add(1);
        self.audit.append(
            now_ms,
            format!("gen={} verified {kind:?}:{id}", self.generation),
        );
        Ok(())
    }

    pub fn check_plan(&self, snapshot: &Snapshot, used: &[(Kind, &str)]) -> InventoryResult<()> {
        if snapshot.generation == self.generation {
            return Ok(());
        }
        for (kind, id) in used {
            let then = snapshot
                .items
                .iter()
                .find(|i| i.kind == *kind && i.id == *id)
                .ok_or_else(|| InventoryError::Unknown((*id).to_owned()))?;
            let now = self
                .items
                .get(&(*kind, (*id).to_owned()))
                .ok_or_else(|| InventoryError::Stale((*id).to_owned()))?;
            if now.state != State::Active || now.hash != then.hash {
                return Err(InventoryError::Stale((*id).to_owned()));
            }
        }
        Ok(())
    }
}
