use serde::{Deserialize, Serialize};

use crate::error::LearnError;

pub const LIMIT_MAX: f32 = 0.3;
pub const EXPLORE_MAX: f32 = 0.05;
const HOUR_MS: u64 = 3_600_000;
const DAY_MS: u64 = 86_400_000;

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct LearnerPolicy {
    pub half_life_ms: u64,
    pub metrics_half_life_ms: u64,
    pub prior: f32,
    pub limit: f32,
    pub explore_rate: f32,
    pub explore_bonus: f32,
    pub min_place_weight: f32,
    pub max_persons: usize,
    pub max_models: usize,
    pub max_places: usize,
}

impl Default for LearnerPolicy {
    fn default() -> Self {
        Self {
            half_life_ms: 21 * DAY_MS,
            metrics_half_life_ms: 7 * DAY_MS,
            prior: 3.0,
            limit: LIMIT_MAX,
            explore_rate: EXPLORE_MAX,
            explore_bonus: 0.15,
            min_place_weight: 2.0,
            max_persons: 64,
            max_models: 512,
            max_places: 1024,
        }
    }
}

impl LearnerPolicy {
    pub fn validate(&self) -> Result<(), LearnError> {
        let finite = [
            self.prior,
            self.limit,
            self.explore_rate,
            self.explore_bonus,
            self.min_place_weight,
        ]
        .iter()
        .all(|v| v.is_finite());
        let ok = finite
            && self.half_life_ms >= HOUR_MS
            && self.metrics_half_life_ms >= HOUR_MS
            && self.prior > 0.0
            && self.limit > 0.0
            && self.limit <= LIMIT_MAX
            && (0.0..=EXPLORE_MAX).contains(&self.explore_rate)
            && (0.0..=LIMIT_MAX).contains(&self.explore_bonus)
            && self.min_place_weight > 0.0
            && (1..=1024).contains(&self.max_persons)
            && (1..=4096).contains(&self.max_models)
            && (1..=8192).contains(&self.max_places);
        if ok {
            Ok(())
        } else {
            Err(LearnError::InvalidPolicy)
        }
    }
}

#[allow(clippy::cast_precision_loss)]
#[must_use]
pub fn decay(elapsed_ms: u64, half_life_ms: u64) -> f32 {
    if elapsed_ms == 0 || half_life_ms == 0 {
        return 1.0;
    }
    let halves = elapsed_ms as f64 / half_life_ms as f64;
    #[allow(clippy::cast_possible_truncation)]
    let factor = 0.5_f64.powf(halves) as f32;
    factor.clamp(0.0, 1.0)
}
