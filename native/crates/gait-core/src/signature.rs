use serde::{Deserialize, Serialize};

use crate::error::GaitError;

pub const GAIT_DIM: usize = 16;

const FEATURE_WEIGHTS: [f32; GAIT_DIM] = [
    1.5, 1.2, 1.2, 1.0, 1.2, 1.0, 0.8, 1.0, 0.8, 0.8, 0.7, 0.7, 0.6, 0.6, 0.5, 0.5,
];

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GaitSignature {
    pub features: [f32; GAIT_DIM],
    pub samples: usize,
    pub confidence: f32,
}

impl GaitSignature {
    #[must_use]
    pub const fn new(features: [f32; GAIT_DIM], samples: usize, confidence: f32) -> Self {
        Self {
            features,
            samples,
            confidence,
        }
    }

    pub fn from_slice(slice: &[f32], samples: usize, confidence: f32) -> Result<Self, GaitError> {
        if slice.len() != GAIT_DIM {
            return Err(GaitError::InvalidSignatureLength);
        }
        let mut features = [0.0_f32; GAIT_DIM];
        for (i, val) in slice.iter().enumerate() {
            if !val.is_finite() || val.abs() > 1000.0 {
                return Err(GaitError::InvalidSignatureValue);
            }
            if let Some(slot) = features.get_mut(i) {
                *slot = *val;
            }
        }
        let clamped_confidence = if confidence.is_finite() {
            confidence.clamp(0.0, 1.0)
        } else {
            0.0
        };
        Ok(Self {
            features,
            samples,
            confidence: clamped_confidence,
        })
    }

    #[must_use]
    pub fn to_vec(&self) -> Vec<f32> {
        self.features.to_vec()
    }

    #[must_use]
    pub fn cosine_similarity(&self, other: &Self) -> f32 {
        let mut dot = 0.0_f32;
        let mut norm_a = 0.0_f32;
        let mut norm_b = 0.0_f32;
        for (a, b) in self.features.iter().zip(other.features.iter()) {
            dot += *a * *b;
            norm_a += *a * *a;
            norm_b += *b * *b;
        }
        if norm_a <= 1e-6 || norm_b <= 1e-6 {
            return 0.0;
        }
        (dot / (norm_a.sqrt() * norm_b.sqrt())).clamp(0.0, 1.0)
    }

    #[must_use]
    pub fn weighted_similarity(&self, other: &Self) -> f32 {
        let mut total_weight = 0.0_f32;
        let mut weighted_diff = 0.0_f32;
        for ((a, b), w) in self
            .features
            .iter()
            .zip(other.features.iter())
            .zip(FEATURE_WEIGHTS.iter())
        {
            let diff = (*a - *b).abs();
            let denom = a.abs().max(b.abs()).max(0.1);
            let rel_diff = (diff / denom).clamp(0.0, 1.0);
            weighted_diff += rel_diff * *w;
            total_weight += *w;
        }
        if total_weight <= 1e-6 {
            return 0.0;
        }
        (1.0 - (weighted_diff / total_weight)).clamp(0.0, 1.0)
    }

    pub fn aggregate(signatures: &[Self]) -> Result<Self, GaitError> {
        if signatures.is_empty() {
            return Err(GaitError::InsufficientSamples);
        }
        let mut sum_features = [0.0_f32; GAIT_DIM];
        let mut total_samples = 0_usize;
        let mut total_conf = 0.0_f32;
        for sig in signatures {
            total_samples = total_samples.saturating_add(sig.samples);
            total_conf += sig.confidence;
            for (i, f) in sig.features.iter().enumerate() {
                if let Some(slot) = sum_features.get_mut(i) {
                    *slot += *f;
                }
            }
        }
        #[allow(clippy::cast_precision_loss)]
        let count_f = signatures.len() as f32;
        let mut avg_features = [0.0_f32; GAIT_DIM];
        for (i, sum) in sum_features.iter().enumerate() {
            if let Some(slot) = avg_features.get_mut(i) {
                *slot = *sum / count_f;
            }
        }
        let mean_conf = (total_conf / count_f).clamp(0.0, 1.0);
        Ok(Self {
            features: avg_features,
            samples: total_samples,
            confidence: mean_conf,
        })
    }
}
