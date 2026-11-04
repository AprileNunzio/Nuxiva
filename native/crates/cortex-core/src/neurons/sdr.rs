use serde::{Deserialize, Serialize};

pub const SDR_BIT_SIZE: usize = 2048;
pub const SDR_WORD_COUNT: usize = 32;
pub const SDR_DEFAULT_K: usize = 40;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct SparseDistributedRepresentation {
    words: [u64; SDR_WORD_COUNT],
}

impl Default for SparseDistributedRepresentation {
    fn default() -> Self {
        Self {
            words: [0u64; SDR_WORD_COUNT],
        }
    }
}

impl SparseDistributedRepresentation {
    #[must_use]
    pub const fn zero() -> Self {
        Self {
            words: [0u64; SDR_WORD_COUNT],
        }
    }

    #[must_use]
    pub fn from_words(words: [u64; SDR_WORD_COUNT]) -> Self {
        Self { words }
    }

    #[must_use]
    pub fn words(&self) -> &[u64; SDR_WORD_COUNT] {
        &self.words
    }

    pub fn set_bit(&mut self, bit_idx: usize) {
        if bit_idx < SDR_BIT_SIZE {
            let word_idx = bit_idx >> 6;
            let offset = bit_idx & 63;
            if let Some(w) = self.words.get_mut(word_idx) {
                *w |= 1u64 << offset;
            }
        }
    }

    #[must_use]
    pub fn get_bit(&self, bit_idx: usize) -> bool {
        if bit_idx < SDR_BIT_SIZE {
            let word_idx = bit_idx >> 6;
            let offset = bit_idx & 63;
            self.words
                .get(word_idx)
                .is_some_and(|w| (*w & (1u64 << offset)) != 0)
        } else {
            false
        }
    }

    #[must_use]
    pub fn population(&self) -> usize {
        let mut count = 0usize;
        for w in &self.words {
            count = count.saturating_add(w.count_ones() as usize);
        }
        count
    }

    #[must_use]
    pub fn overlap(&self, other: &Self) -> usize {
        let mut count = 0usize;
        for (w1, w2) in self.words.iter().zip(other.words.iter()) {
            count = count.saturating_add((w1 & w2).count_ones() as usize);
        }
        count
    }

    #[must_use]
    pub fn jaccard_similarity(&self, other: &Self) -> f64 {
        let intersection = self.overlap(other);
        let union_pop = self.union(other).population();
        if union_pop == 0 {
            0.0
        } else {
            intersection as f64 / union_pop as f64
        }
    }

    #[must_use]
    pub fn union(&self, other: &Self) -> Self {
        let mut result = [0u64; SDR_WORD_COUNT];
        for (idx, (w1, w2)) in self.words.iter().zip(other.words.iter()).enumerate() {
            if let Some(res) = result.get_mut(idx) {
                *res = *w1 | *w2;
            }
        }
        Self { words: result }
    }

    #[must_use]
    pub fn intersection(&self, other: &Self) -> Self {
        let mut result = [0u64; SDR_WORD_COUNT];
        for (idx, (w1, w2)) in self.words.iter().zip(other.words.iter()).enumerate() {
            if let Some(res) = result.get_mut(idx) {
                *res = *w1 & *w2;
            }
        }
        Self { words: result }
    }

    #[must_use]
    pub fn encode_dense_k_wta(dense: &[f32], k: usize) -> Self {
        let mut indexed: Vec<(usize, f32)> = dense.iter().copied().enumerate().collect();
        indexed.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

        let mut sdr = Self::zero();
        let top_k = k.min(indexed.len()).min(SDR_BIT_SIZE);
        for item in indexed.iter().take(top_k) {
            let bit_idx = (item.0.saturating_mul(97).saturating_add(13)) % SDR_BIT_SIZE;
            sdr.set_bit(bit_idx);
        }
        sdr
    }
}
