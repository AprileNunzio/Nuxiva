use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MemoryEntry {
    pub key: String,
    pub embedding: Vec<f32>,
    pub response_key: String,
    pub payload_json: String,
    pub hit_count: u32,
    pub timestamp_ms: u64,
}

impl MemoryEntry {
    #[must_use]
    pub fn new(
        key: impl Into<String>,
        embedding: Vec<f32>,
        response_key: impl Into<String>,
        payload_json: impl Into<String>,
        timestamp_ms: u64,
    ) -> Self {
        Self {
            key: key.into(),
            embedding,
            response_key: response_key.into(),
            payload_json: payload_json.into(),
            hit_count: 0,
            timestamp_ms,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MemoryHit {
    pub key: String,
    pub response_key: String,
    pub payload_json: String,
    pub similarity: f32,
    pub hit_count: u32,
}

#[derive(Debug, Clone, PartialEq)]
pub struct FastSemanticMemory {
    entries: Vec<MemoryEntry>,
    max_capacity: usize,
}

impl Default for FastSemanticMemory {
    fn default() -> Self {
        Self::new(512)
    }
}

impl FastSemanticMemory {
    #[must_use]
    pub fn new(max_capacity: usize) -> Self {
        Self {
            entries: Vec::with_capacity(max_capacity),
            max_capacity,
        }
    }

    #[must_use]
    pub fn compute_cosine_similarity(vec_a: &[f32], vec_b: &[f32]) -> f32 {
        if vec_a.is_empty() || vec_a.len() != vec_b.len() {
            return 0.0;
        }

        let mut dot = 0.0_f32;
        let mut norm_a = 0.0_f32;
        let mut norm_b = 0.0_f32;

        for (a, b) in vec_a.iter().zip(vec_b.iter()) {
            dot += a * b;
            norm_a += a * a;
            norm_b += b * b;
        }

        let denominator = norm_a.sqrt() * norm_b.sqrt();
        if denominator < 1e-7 {
            return 0.0;
        }

        (dot / denominator).clamp(-1.0, 1.0)
    }

    pub fn insert(&mut self, mut entry: MemoryEntry) {
        if let Some(existing) = self.entries.iter_mut().find(|e| e.key == entry.key) {
            existing.embedding = entry.embedding;
            existing.response_key = entry.response_key;
            existing.payload_json = entry.payload_json;
            existing.timestamp_ms = entry.timestamp_ms;
            return;
        }

        if self.entries.len() >= self.max_capacity {
            self.prune_lru(self.max_capacity.saturating_sub(1));
        }

        entry.hit_count = 0;
        self.entries.push(entry);
    }

    pub fn lookup(
        &mut self,
        exact_key: &str,
        query_embedding: &[f32],
        similarity_threshold: f32,
    ) -> Option<MemoryHit> {
        if let Some(exact) = self.entries.iter_mut().find(|e| e.key == exact_key) {
            exact.hit_count = exact.hit_count.saturating_add(1);
            return Some(MemoryHit {
                key: exact.key.clone(),
                response_key: exact.response_key.clone(),
                payload_json: exact.payload_json.clone(),
                similarity: 1.0,
                hit_count: exact.hit_count,
            });
        }

        if query_embedding.is_empty() {
            return None;
        }

        let mut best_idx: Option<usize> = None;
        let mut best_sim = similarity_threshold;

        for (idx, entry) in self.entries.iter().enumerate() {
            let sim = Self::compute_cosine_similarity(&entry.embedding, query_embedding);
            if sim > best_sim {
                best_sim = sim;
                best_idx = Some(idx);
            }
        }

        if let Some(target_idx) = best_idx {
            if let Some(entry) = self.entries.get_mut(target_idx) {
                entry.hit_count = entry.hit_count.saturating_add(1);
                return Some(MemoryHit {
                    key: entry.key.clone(),
                    response_key: entry.response_key.clone(),
                    payload_json: entry.payload_json.clone(),
                    similarity: best_sim,
                    hit_count: entry.hit_count,
                });
            }
        }

        None
    }

    pub fn prune_lru(&mut self, target_size: usize) {
        if self.entries.len() <= target_size {
            return;
        }

        self.entries
            .sort_by(|a, b| (b.hit_count, b.timestamp_ms).cmp(&(a.hit_count, a.timestamp_ms)));
        self.entries.truncate(target_size);
    }

    pub fn clear(&mut self) {
        self.entries.clear();
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.entries.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }
}
