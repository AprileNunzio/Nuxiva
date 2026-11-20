use crate::error::TernaryError;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct TernaryVector {
    dim: usize,
    pos_masks: Vec<u64>,
    neg_masks: Vec<u64>,
}

impl TernaryVector {
    pub fn from_raw(
        dim: usize,
        pos_masks: Vec<u64>,
        neg_masks: Vec<u64>,
    ) -> Result<Self, TernaryError> {
        if dim == 0 {
            return Err(TernaryError::EmptyVector);
        }
        let expected_words = (dim.saturating_add(63)) / 64;
        if pos_masks.len() != expected_words || neg_masks.len() != expected_words {
            return Err(TernaryError::DimensionMismatch {
                expected: expected_words,
                actual: pos_masks.len(),
            });
        }
        for (index, (p, n)) in pos_masks.iter().zip(neg_masks.iter()).enumerate() {
            if (*p & *n) != 0 {
                return Err(TernaryError::OverlappingMasks { index });
            }
        }
        Ok(Self {
            dim,
            pos_masks,
            neg_masks,
        })
    }

    pub fn from_trits(trits: &[i8]) -> Result<Self, TernaryError> {
        if trits.is_empty() {
            return Err(TernaryError::EmptyVector);
        }
        let dim = trits.len();
        let words_count = (dim.saturating_add(63)) / 64;
        let mut pos_masks = vec![0u64; words_count];
        let mut neg_masks = vec![0u64; words_count];

        for (idx, &trit) in trits.iter().enumerate() {
            let word_idx = idx / 64;
            let bit_idx = idx % 64;
            let mask = 1u64 << bit_idx;
            match trit {
                1 => {
                    if let Some(w) = pos_masks.get_mut(word_idx) {
                        *w |= mask;
                    }
                }
                -1 => {
                    if let Some(w) = neg_masks.get_mut(word_idx) {
                        *w |= mask;
                    }
                }
                0 => {}
                other => return Err(TernaryError::InvalidTrit { value: other }),
            }
        }

        Ok(Self {
            dim,
            pos_masks,
            neg_masks,
        })
    }

    #[must_use]
    pub fn dim(&self) -> usize {
        self.dim
    }

    #[must_use]
    pub fn pos_masks(&self) -> &[u64] {
        &self.pos_masks
    }

    #[must_use]
    pub fn neg_masks(&self) -> &[u64] {
        &self.neg_masks
    }

    #[must_use]
    pub fn to_trits(&self) -> Vec<i8> {
        let mut out = Vec::with_capacity(self.dim);
        for idx in 0..self.dim {
            let word_idx = idx / 64;
            let bit_idx = idx % 64;
            let mask = 1u64 << bit_idx;
            let p = self.pos_masks.get(word_idx).copied().unwrap_or(0);
            let n = self.neg_masks.get(word_idx).copied().unwrap_or(0);
            if (p & mask) != 0 {
                out.push(1);
            } else if (n & mask) != 0 {
                out.push(-1);
            } else {
                out.push(0);
            }
        }
        out
    }

    #[must_use]
    pub fn active_dimensions(&self) -> usize {
        let mut count: usize = 0;
        for (p, n) in self.pos_masks.iter().zip(self.neg_masks.iter()) {
            count = count.saturating_add((*p | *n).count_ones() as usize);
        }
        count
    }

    pub fn dot(&self, other: &Self) -> Result<i32, TernaryError> {
        if self.dim != other.dim {
            return Err(TernaryError::DimensionMismatch {
                expected: self.dim,
                actual: other.dim,
            });
        }
        let mut score: i32 = 0;
        for (p_u, (n_u, (p_v, n_v))) in self.pos_masks.iter().zip(
            self.neg_masks
                .iter()
                .zip(other.pos_masks.iter().zip(other.neg_masks.iter())),
        ) {
            let pos_matches = (*p_u & *p_v) | (*n_u & *n_v);
            let neg_matches = (*p_u & *n_v) | (*n_u & *p_v);
            let pos_count = i32::try_from(pos_matches.count_ones()).unwrap_or(0);
            let neg_count = i32::try_from(neg_matches.count_ones()).unwrap_or(0);
            score = score.saturating_add(pos_count).saturating_sub(neg_count);
        }
        Ok(score)
    }

    #[allow(clippy::cast_precision_loss)]
    pub fn cosine_similarity(&self, other: &Self) -> Result<f32, TernaryError> {
        let dot = self.dot(other)?;
        let active_u = self.active_dimensions();
        let active_v = other.active_dimensions();
        if active_u == 0 || active_v == 0 {
            return Ok(0.0);
        }
        let denom = ((active_u as f32) * (active_v as f32)).sqrt();
        if denom <= f32::EPSILON {
            Ok(0.0)
        } else {
            Ok((dot as f32) / denom)
        }
    }
}
