use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CacheEntry {
    pub key: String,
    pub content: String,
    pub thought: String,
    pub artifacts_json: String,
    pub model_mode: String,
    pub created_at_ms: u64,
    pub ttl_ms: u64,
    pub hit_count: u64,
    pub size_bytes: usize,
}

#[derive(Debug, Clone, Copy, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct CacheStats {
    pub total_entries: usize,
    pub total_bytes: usize,
    pub hits: u64,
    pub misses: u64,
    pub evictions: u64,
}

#[derive(Debug, Clone)]
pub struct StudioCache {
    entries: BTreeMap<String, CacheEntry>,
    access_order: Vec<String>,
    max_entries: usize,
    max_bytes: usize,
    current_bytes: usize,
    hits: u64,
    misses: u64,
    evictions: u64,
}

impl StudioCache {
    #[must_use]
    pub const fn new(max_entries: usize, max_bytes: usize) -> Self {
        Self {
            entries: BTreeMap::new(),
            access_order: Vec::new(),
            max_entries,
            max_bytes,
            current_bytes: 0,
            hits: 0,
            misses: 0,
            evictions: 0,
        }
    }

    #[must_use]
    pub fn derive_key(prompt: &str, model_mode: &str, project_id: Option<&str>) -> String {
        let cleaned: String = prompt
            .trim()
            .to_lowercase()
            .split_whitespace()
            .collect::<Vec<_>>()
            .join(" ");
        let proj = project_id.unwrap_or("");
        let mut hasher = 0xcbf2_9ce4_8422_2325_u64;
        for b in cleaned.bytes() {
            hasher ^= u64::from(b);
            hasher = hasher.wrapping_mul(0x0100_0000_01b3_u64);
        }
        for b in model_mode.bytes() {
            hasher ^= u64::from(b);
            hasher = hasher.wrapping_mul(0x0100_0000_01b3_u64);
        }
        for b in proj.bytes() {
            hasher ^= u64::from(b);
            hasher = hasher.wrapping_mul(0x0100_0000_01b3_u64);
        }
        format!("{model_mode}_{hasher:016x}")
    }

    pub fn get(&mut self, key: &str, now_ms: u64) -> Option<CacheEntry> {
        let entry = self.entries.get(key)?.clone();
        if entry.ttl_ms > 0 && entry.created_at_ms.saturating_add(entry.ttl_ms) < now_ms {
            self.remove(key);
            self.evictions = self.evictions.saturating_add(1);
            self.misses = self.misses.saturating_add(1);
            return None;
        }

        self.touch(key);
        if let Some(e) = self.entries.get_mut(key) {
            e.hit_count = e.hit_count.saturating_add(1);
        }
        self.hits = self.hits.saturating_add(1);
        Some(entry)
    }

    #[allow(clippy::too_many_arguments)]
    pub fn put(
        &mut self,
        key: String,
        content: String,
        thought: String,
        artifacts_json: String,
        model_mode: String,
        ttl_seconds: u64,
        now_ms: u64,
    ) {
        let entry_size = key
            .len()
            .saturating_add(content.len())
            .saturating_add(thought.len())
            .saturating_add(artifacts_json.len())
            .saturating_add(model_mode.len())
            .saturating_add(64);

        if let Some(old) = self.entries.remove(&key) {
            self.current_bytes = self.current_bytes.saturating_sub(old.size_bytes);
            self.access_order.retain(|k| k != &key);
        }

        while !self.access_order.is_empty()
            && (self.entries.len() >= self.max_entries
                || self.current_bytes.saturating_add(entry_size) > self.max_bytes)
        {
            if let Some(oldest_key) = self.access_order.first().cloned() {
                self.remove(&oldest_key);
                self.evictions = self.evictions.saturating_add(1);
            } else {
                break;
            }
        }

        let entry = CacheEntry {
            key: key.clone(),
            content,
            thought,
            artifacts_json,
            model_mode,
            created_at_ms: now_ms,
            ttl_ms: ttl_seconds.saturating_mul(1000),
            hit_count: 0,
            size_bytes: entry_size,
        };

        self.current_bytes = self.current_bytes.saturating_add(entry_size);
        self.entries.insert(key.clone(), entry);
        self.access_order.push(key);
    }

    pub fn trim_to_bytes(&mut self, target_bytes: usize) -> usize {
        let start_bytes = self.current_bytes;
        while self.current_bytes > target_bytes && !self.access_order.is_empty() {
            if let Some(oldest_key) = self.access_order.first().cloned() {
                self.remove(&oldest_key);
                self.evictions = self.evictions.saturating_add(1);
            } else {
                break;
            }
        }
        start_bytes.saturating_sub(self.current_bytes)
    }

    pub fn clear(&mut self) {
        self.entries.clear();
        self.access_order.clear();
        self.current_bytes = 0;
    }

    #[must_use]
    pub const fn current_bytes(&self) -> usize {
        self.current_bytes
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
    pub fn stats(&self) -> CacheStats {
        CacheStats {
            total_entries: self.entries.len(),
            total_bytes: self.current_bytes,
            hits: self.hits,
            misses: self.misses,
            evictions: self.evictions,
        }
    }

    fn remove(&mut self, key: &str) {
        if let Some(old) = self.entries.remove(key) {
            self.current_bytes = self.current_bytes.saturating_sub(old.size_bytes);
        }
        self.access_order.retain(|k| k != key);
    }

    fn touch(&mut self, key: &str) {
        self.access_order.retain(|k| k != key);
        self.access_order.push(key.to_string());
    }
}

#[cfg(test)]
#[allow(
    clippy::indexing_slicing,
    clippy::panic,
    clippy::manual_string_new,
    clippy::unwrap_used
)]
mod tests {
    use super::*;

    #[test]
    fn put_and_get_success() {
        let mut cache = StudioCache::new(10, 10_000);
        let key = StudioCache::derive_key("hello world", "reasoning", None);
        cache.put(
            key.clone(),
            "output text".into(),
            "thought text".into(),
            "[]".into(),
            "reasoning".into(),
            3600,
            1000,
        );
        let item = cache.get(&key, 1500);
        assert!(item.is_some());
        if let Some(unwrapped) = item {
            assert_eq!(unwrapped.content, "output text");
        }
        assert_eq!(cache.stats().hits, 1);
    }

    #[test]
    fn ttl_expiration_removes_entry() {
        let mut cache = StudioCache::new(10, 10_000);
        let key = StudioCache::derive_key("temp query", "fast", None);
        cache.put(
            key.clone(),
            "temp result".into(),
            "".into(),
            "[]".into(),
            "fast".into(),
            10,
            1000,
        );
        assert!(cache.get(&key, 12_000).is_none());
        assert_eq!(cache.stats().misses, 1);
        assert_eq!(cache.stats().evictions, 1);
    }

    #[test]
    fn lru_eviction_when_capacity_exceeded() {
        let mut cache = StudioCache::new(2, 10_000);
        let k1 = StudioCache::derive_key("q1", "fast", None);
        let k2 = StudioCache::derive_key("q2", "fast", None);
        let k3 = StudioCache::derive_key("q3", "fast", None);
        cache.put(
            k1.clone(),
            "r1".into(),
            "".into(),
            "[]".into(),
            "fast".into(),
            3600,
            100,
        );
        cache.put(
            k2.clone(),
            "r2".into(),
            "".into(),
            "[]".into(),
            "fast".into(),
            3600,
            101,
        );
        cache.put(
            k3.clone(),
            "r3".into(),
            "".into(),
            "[]".into(),
            "fast".into(),
            3600,
            102,
        );

        assert!(cache.get(&k1, 200).is_none());
        assert!(cache.get(&k2, 200).is_some());
        assert!(cache.get(&k3, 200).is_some());
        assert_eq!(cache.len(), 2);
    }

    #[test]
    fn trim_to_target_bytes() {
        let mut cache = StudioCache::new(100, 100_000);
        for i in 0..10 {
            let key = format!("k_{i}");
            cache.put(
                key,
                "some large payload content here".into(),
                "".into(),
                "[]".into(),
                "fast".into(),
                3600,
                100,
            );
        }
        let initial_size = cache.current_bytes();
        assert!(initial_size > 500);
        let freed = cache.trim_to_bytes(200);
        assert!(freed > 0);
        assert!(cache.current_bytes() <= 200);
    }
}
