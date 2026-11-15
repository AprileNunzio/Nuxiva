use crate::capability::{Capabilities, Load};
use crate::error::{PeerError, PeerResult};
use crate::ident::check_id;
use std::collections::BTreeMap;

pub const MAX_NODES: usize = 256;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Liveness {
    pub suspect_after_ms: i64,
    pub dead_after_ms: i64,
}

impl Default for Liveness {
    fn default() -> Self {
        Self {
            suspect_after_ms: 6_000,
            dead_after_ms: 15_000,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Status {
    Alive,
    Suspect,
    Dead,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Entry {
    pub caps: Capabilities,
    pub load: Load,
    pub caps_seq: u64,
    pub load_seq: u64,
    pub last_seen: i64,
    pub status: Status,
}

#[derive(Debug, Clone, Default)]
pub struct Registry {
    nodes: BTreeMap<String, Entry>,
    liveness: Liveness,
}

impl Registry {
    #[must_use]
    pub fn new(liveness: Liveness) -> Self {
        Self {
            nodes: BTreeMap::new(),
            liveness,
        }
    }

    pub fn announce(
        &mut self,
        id: &str,
        seq: u64,
        caps: Capabilities,
        now: i64,
    ) -> PeerResult<bool> {
        check_id(id)?;
        caps.validate()?;
        if let Some(entry) = self.nodes.get_mut(id) {
            if seq <= entry.caps_seq {
                return Ok(false);
            }
            entry.caps = caps;
            entry.caps_seq = seq;
            entry.last_seen = entry.last_seen.max(now);
            entry.status = Status::Alive;
            return Ok(true);
        }
        if self.nodes.len() >= MAX_NODES {
            return Err(PeerError::Capacity);
        }
        self.nodes.insert(
            id.to_owned(),
            Entry {
                caps,
                load: Load::default(),
                caps_seq: seq,
                load_seq: 0,
                last_seen: now,
                status: Status::Alive,
            },
        );
        Ok(true)
    }

    pub fn heartbeat(&mut self, id: &str, seq: u64, load: Load, now: i64) -> PeerResult<bool> {
        load.validate()?;
        let entry = self.nodes.get_mut(id).ok_or(PeerError::Unknown)?;
        if seq <= entry.load_seq {
            return Ok(false);
        }
        entry.load = load;
        entry.load_seq = seq;
        entry.last_seen = entry.last_seen.max(now);
        entry.status = Status::Alive;
        Ok(true)
    }

    pub fn touch(&mut self, id: &str, now: i64) {
        if let Some(entry) = self.nodes.get_mut(id) {
            entry.last_seen = entry.last_seen.max(now);
            entry.status = Status::Alive;
        }
    }

    pub fn leave(&mut self, id: &str) {
        if let Some(entry) = self.nodes.get_mut(id) {
            entry.status = Status::Dead;
        }
    }

    pub fn sweep(&mut self, now: i64) -> Vec<String> {
        let mut changed = Vec::new();
        for (id, entry) in &mut self.nodes {
            let silent = now.saturating_sub(entry.last_seen);
            let next = if silent >= self.liveness.dead_after_ms {
                Status::Dead
            } else if silent >= self.liveness.suspect_after_ms {
                Status::Suspect
            } else {
                Status::Alive
            };
            if next != entry.status {
                entry.status = next;
                changed.push(id.clone());
            }
        }
        changed
    }

    #[must_use]
    pub fn get(&self, id: &str) -> Option<&Entry> {
        self.nodes.get(id)
    }

    #[must_use]
    pub fn is_alive(&self, id: &str) -> bool {
        self.nodes
            .get(id)
            .is_some_and(|e| e.status == Status::Alive)
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.nodes.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.nodes.is_empty()
    }

    pub fn iter(&self) -> impl Iterator<Item = (&String, &Entry)> {
        self.nodes.iter()
    }

    pub fn alive(&self) -> impl Iterator<Item = (&String, &Entry)> {
        self.nodes.iter().filter(|(_, e)| e.status == Status::Alive)
    }
}
