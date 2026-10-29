use std::collections::HashMap;
use std::sync::Arc;

#[derive(Debug)]
pub struct BlobCache {
    budget: usize,
    used: usize,
    tick: u64,
    items: HashMap<String, (Arc<Vec<u8>>, u64)>,
}

fn valid_key(key: &str) -> bool {
    key.len() == 64 && key.bytes().all(|b| matches!(b, b'0'..=b'9' | b'a'..=b'f'))
}

impl BlobCache {
    #[must_use]
    pub fn new(budget: usize) -> Self {
        Self {
            budget,
            used: 0,
            tick: 0,
            items: HashMap::new(),
        }
    }

    pub fn get(&mut self, key: &str) -> Option<Arc<Vec<u8>>> {
        self.tick = self.tick.wrapping_add(1);
        let now = self.tick;
        self.items.get_mut(key).map(|(blob, seen)| {
            *seen = now;
            Arc::clone(blob)
        })
    }

    pub fn put(&mut self, key: &str, blob: Vec<u8>) -> bool {
        if !valid_key(key) || blob.len() > self.budget {
            return false;
        }
        if let Some((old, _)) = self.items.remove(key) {
            self.used = self.used.saturating_sub(old.len());
        }
        while self.used.saturating_add(blob.len()) > self.budget {
            let Some(oldest) = self
                .items
                .iter()
                .min_by_key(|(_, (_, seen))| *seen)
                .map(|(k, _)| k.clone())
            else {
                break;
            };
            if let Some((old, _)) = self.items.remove(&oldest) {
                self.used = self.used.saturating_sub(old.len());
            }
        }
        self.tick = self.tick.wrapping_add(1);
        self.used = self.used.saturating_add(blob.len());
        self.items
            .insert(key.to_owned(), (Arc::new(blob), self.tick));
        true
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.items.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.items.is_empty()
    }

    #[must_use]
    pub const fn used(&self) -> usize {
        self.used
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn key(c: char) -> String {
        std::iter::repeat_n(c, 64).collect()
    }

    #[test]
    fn evicts_least_recently_used_within_budget() {
        let mut cache = BlobCache::new(10);
        assert!(cache.put(&key('a'), vec![0; 4]));
        assert!(cache.put(&key('b'), vec![0; 4]));
        assert!(cache.get(&key('a')).is_some());
        assert!(cache.put(&key('c'), vec![0; 4]));
        assert!(cache.get(&key('b')).is_none());
        assert!(cache.get(&key('a')).is_some());
        assert!(cache.used() <= 10);
    }

    #[test]
    fn rejects_bad_keys_and_oversized_blobs() {
        let mut cache = BlobCache::new(8);
        assert!(!cache.put("../etc/passwd", vec![1]));
        assert!(!cache.put(&key('A'), vec![1]));
        assert!(!cache.put(&key('a'), vec![0; 9]));
        assert!(cache.is_empty());
    }
}
