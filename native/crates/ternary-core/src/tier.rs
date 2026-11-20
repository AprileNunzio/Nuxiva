use crate::error::TernaryError;
use crate::vector::TernaryVector;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum TierState {
    Hot,
    Warm,
    Cold,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TieredMemoryItem {
    pub id: String,
    pub tier: TierState,
    pub weight: f32,
    pub stability_base: f32,
    pub recall_count: u32,
    pub created_at_ms: u64,
    pub last_accessed_ms: u64,
    pub is_immune: bool,
    pub project_id: Option<String>,
    pub cluster_id: Option<u64>,
    pub payload: Vec<u8>,
    pub vector: Option<TernaryVector>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TierManager {
    warm_threshold: f32,
    cold_threshold: f32,
    expansion_factor: f32,
    items: HashMap<String, TieredMemoryItem>,
}

impl TierManager {
    pub fn new(
        warm_threshold: f32,
        cold_threshold: f32,
        expansion_factor: f32,
    ) -> Result<Self, TernaryError> {
        if !(0.0..=1.0).contains(&warm_threshold) || !(0.0..=1.0).contains(&cold_threshold) {
            return Err(TernaryError::InvalidRetentionParameter {
                reason: "threshold must be between 0.0 and 1.0".to_string(),
            });
        }
        if warm_threshold < cold_threshold {
            return Err(TernaryError::InvalidRetentionParameter {
                reason: "warm_threshold cannot be smaller than cold_threshold".to_string(),
            });
        }
        if expansion_factor < 1.0 {
            return Err(TernaryError::InvalidRetentionParameter {
                reason: "expansion_factor must be >= 1.0".to_string(),
            });
        }
        Ok(Self {
            warm_threshold,
            cold_threshold,
            expansion_factor,
            items: HashMap::new(),
        })
    }

    pub fn insert(&mut self, item: TieredMemoryItem) {
        self.items.insert(item.id.clone(), item);
    }

    #[must_use]
    pub fn get(&self, id: &str) -> Option<&TieredMemoryItem> {
        self.items.get(id)
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
    #[allow(clippy::cast_precision_loss)]
    pub fn compute_retention(
        item: &TieredMemoryItem,
        current_time_ms: u64,
        expansion_factor: f32,
    ) -> f32 {
        if item.is_immune {
            return 1.0;
        }
        let elapsed_ms = current_time_ms.saturating_sub(item.last_accessed_ms);
        let elapsed_sec = (elapsed_ms as f32) / 1000.0;
        let k = item.recall_count.min(20);
        let stability_multiplier = expansion_factor.powi(i32::try_from(k).unwrap_or(0));
        let stability = item.stability_base.max(1.0) * stability_multiplier;
        let decay = (-elapsed_sec / stability).exp();
        item.weight.clamp(0.0, 1.0) * decay
    }

    #[must_use]
    pub fn calculate_retention(&self, item: &TieredMemoryItem, current_time_ms: u64) -> f32 {
        Self::compute_retention(item, current_time_ms, self.expansion_factor)
    }

    pub fn record_access(&mut self, id: &str, current_time_ms: u64) -> Result<(), TernaryError> {
        let item = self
            .items
            .get_mut(id)
            .ok_or_else(|| TernaryError::NodeNotFound { id: id.to_string() })?;
        item.last_accessed_ms = current_time_ms;
        item.recall_count = item.recall_count.saturating_add(1);
        if item.tier == TierState::Cold {
            item.tier = TierState::Warm;
        }
        Ok(())
    }

    pub fn evaluate_and_prune(
        &mut self,
        current_time_ms: u64,
    ) -> Vec<(String, TierState, TierState)> {
        let mut transitions = Vec::new();
        let factor = self.expansion_factor;
        for item in self.items.values_mut() {
            let retention = Self::compute_retention(item, current_time_ms, factor);

            let previous_tier = item.tier;
            if retention < self.cold_threshold {
                if item.tier != TierState::Cold {
                    item.tier = TierState::Cold;
                    item.vector = None;
                    transitions.push((item.id.clone(), previous_tier, TierState::Cold));
                }
            } else if retention < self.warm_threshold {
                if item.tier == TierState::Hot {
                    item.tier = TierState::Warm;
                    transitions.push((item.id.clone(), previous_tier, TierState::Warm));
                }
            }
        }
        transitions
    }

    pub fn hydrate(
        &mut self,
        id: &str,
        restored_vector: TernaryVector,
    ) -> Result<(), TernaryError> {
        let item = self
            .items
            .get_mut(id)
            .ok_or_else(|| TernaryError::NodeNotFound { id: id.to_string() })?;
        item.tier = TierState::Hot;
        item.vector = Some(restored_vector);
        Ok(())
    }

    #[must_use]
    pub fn count_by_tier(&self, tier: TierState) -> usize {
        self.items.values().filter(|item| item.tier == tier).count()
    }
}
