use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct LwwEntry {
    pub value: String,
    pub timestamp_ms: u64,
    pub node_id: String,
    pub is_deleted: bool,
}

impl LwwEntry {
    #[must_use]
    pub const fn new(value: String, timestamp_ms: u64, node_id: String, is_deleted: bool) -> Self {
        Self {
            value,
            timestamp_ms,
            node_id,
            is_deleted,
        }
    }

    #[must_use]
    pub fn supersedes(&self, other: &Self) -> bool {
        match self.timestamp_ms.cmp(&other.timestamp_ms) {
            std::cmp::Ordering::Greater => true,
            std::cmp::Ordering::Equal => self.node_id > other.node_id,
            std::cmp::Ordering::Less => false,
        }
    }
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct CrdtState {
    entries: BTreeMap<String, LwwEntry>,
}

impl CrdtState {
    #[must_use]
    pub fn new() -> Self {
        Self {
            entries: BTreeMap::new(),
        }
    }

    pub fn set(
        &mut self,
        key: impl Into<String>,
        value: impl Into<String>,
        timestamp_ms: u64,
        node_id: impl Into<String>,
    ) -> bool {
        let entry = LwwEntry::new(value.into(), timestamp_ms, node_id.into(), false);
        let key = key.into();
        if let Some(existing) = self.entries.get(&key) {
            if !entry.supersedes(existing) {
                return false;
            }
        }
        self.entries.insert(key, entry);
        true
    }

    pub fn delete(&mut self, key: &str, timestamp_ms: u64, node_id: impl Into<String>) -> bool {
        let entry = LwwEntry::new(String::new(), timestamp_ms, node_id.into(), true);
        if let Some(existing) = self.entries.get(key) {
            if !entry.supersedes(existing) {
                return false;
            }
        }
        self.entries.insert(key.to_owned(), entry);
        true
    }

    #[must_use]
    pub fn get(&self, key: &str) -> Option<&str> {
        let entry = self.entries.get(key)?;
        if entry.is_deleted {
            None
        } else {
            Some(&entry.value)
        }
    }

    #[must_use]
    pub fn get_entry(&self, key: &str) -> Option<&LwwEntry> {
        self.entries.get(key)
    }

    #[must_use]
    pub fn active_entries(&self) -> BTreeMap<String, String> {
        let mut map = BTreeMap::new();
        for (k, v) in &self.entries {
            if !v.is_deleted {
                map.insert(k.clone(), v.value.clone());
            }
        }
        map
    }

    pub fn merge(&mut self, other: &Self) -> usize {
        let mut updated = 0usize;
        for (k, remote_entry) in &other.entries {
            let should_insert = match self.entries.get(k) {
                Some(local_entry) => remote_entry.supersedes(local_entry),
                None => true,
            };
            if should_insert {
                self.entries.insert(k.clone(), remote_entry.clone());
                updated = updated.saturating_add(1);
            }
        }
        updated
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.entries.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    pub fn to_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string(&self.entries)
    }

    pub fn from_json(json_str: &str) -> Result<Self, serde_json::Error> {
        let entries: BTreeMap<String, LwwEntry> = serde_json::from_str(json_str)?;
        Ok(Self { entries })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_crdt_set_and_merge() {
        let mut node_a = CrdtState::new();
        let mut node_b = CrdtState::new();

        node_a.set("theme", "dark", 1000, "node-a");
        node_b.set("theme", "light", 2000, "node-b");
        node_b.set("sound_volume", "80", 1500, "node-b");

        let updated = node_a.merge(&node_b);
        assert_eq!(updated, 2);
        assert_eq!(node_a.get("theme"), Some("light"));
        assert_eq!(node_a.get("sound_volume"), Some("80"));
    }

    #[test]
    fn test_crdt_delete() {
        let mut state = CrdtState::new();
        state.set("key1", "val1", 100, "node-a");
        assert_eq!(state.get("key1"), Some("val1"));

        state.delete("key1", 200, "node-a");
        assert_eq!(state.get("key1"), None);
    }
}
