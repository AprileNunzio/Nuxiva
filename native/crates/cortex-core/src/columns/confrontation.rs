use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use crate::platform::error::{CortexError, CortexResult};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EpistemicHypothesis {
    pub id: String,
    pub label: String,
    pub prior_probability: f32,
    pub predicted_outcome: String,
    pub action_plan: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EpistemicConfrontationRecord {
    pub id: String,
    pub context_key: String,
    pub uncertainty_entropy: f32,
    pub hypotheses: Vec<EpistemicHypothesis>,
    pub chosen_hypothesis_id: Option<String>,
    pub user_justification: Option<String>,
    pub resolved_certainty: f32,
    pub encrypted_digest: String,
    pub created_at_epoch_ms: u64,
    pub resolved_at_epoch_ms: Option<u64>,
}

#[derive(Debug, Clone)]
pub struct EpistemicDoubtEngine {
    entropy_threshold: f32,
    margin_threshold: f32,
    pending: HashMap<String, EpistemicConfrontationRecord>,
    memory_store: HashMap<String, EpistemicConfrontationRecord>,
}

impl Default for EpistemicDoubtEngine {
    fn default() -> Self {
        Self::new(0.55, 0.15)
    }
}

impl EpistemicDoubtEngine {
    #[must_use]
    pub fn new(entropy_threshold: f32, margin_threshold: f32) -> Self {
        Self {
            entropy_threshold,
            margin_threshold,
            pending: HashMap::new(),
            memory_store: HashMap::new(),
        }
    }

    #[must_use]
    pub fn compute_entropy(hypotheses: &[EpistemicHypothesis]) -> f32 {
        if hypotheses.is_empty() {
            return 0.0;
        }
        let total: f32 = hypotheses
            .iter()
            .map(|h| h.prior_probability.max(0.0))
            .sum();
        if total <= 0.0 {
            return 0.0;
        }
        let mut entropy = 0.0_f32;
        for h in hypotheses {
            let p = h.prior_probability.max(0.0) / total;
            if p > 1e-6 {
                entropy -= p * p.ln();
            }
        }
        entropy
    }

    #[must_use]
    pub fn should_confront(&self, hypotheses: &[EpistemicHypothesis]) -> bool {
        if hypotheses.len() < 2 {
            return false;
        }
        let entropy = Self::compute_entropy(hypotheses);
        if entropy > self.entropy_threshold {
            return true;
        }
        let mut sorted: Vec<f32> = hypotheses.iter().map(|h| h.prior_probability).collect();
        sorted.sort_by(|a, b| b.partial_cmp(a).unwrap_or(std::cmp::Ordering::Equal));
        let first = sorted.first().copied().unwrap_or(0.0);
        let second = sorted.get(1).copied().unwrap_or(0.0);
        let margin = first - second;
        margin < self.margin_threshold
    }

    pub fn initiate_confrontation(
        &mut self,
        id: String,
        context_key: String,
        hypotheses: Vec<EpistemicHypothesis>,
        epoch_ms: u64,
    ) -> CortexResult<EpistemicConfrontationRecord> {
        if id.trim().is_empty() || context_key.trim().is_empty() {
            return Err(CortexError::InvalidIdentifier);
        }
        if hypotheses.len() < 2 {
            return Err(CortexError::EmptyInput);
        }
        let entropy = Self::compute_entropy(&hypotheses);
        let record = EpistemicConfrontationRecord {
            id: id.clone(),
            context_key,
            uncertainty_entropy: entropy,
            hypotheses,
            chosen_hypothesis_id: None,
            user_justification: None,
            resolved_certainty: 0.0,
            encrypted_digest: format!("sha256-pending:{id}"),
            created_at_epoch_ms: epoch_ms,
            resolved_at_epoch_ms: None,
        };
        self.pending.insert(id, record.clone());
        Ok(record)
    }

    pub fn resolve_confrontation(
        &mut self,
        id: &str,
        choice_id: &str,
        justification: &str,
        resolved_epoch_ms: u64,
    ) -> CortexResult<EpistemicConfrontationRecord> {
        let mut record = self.pending.remove(id).ok_or(CortexError::DoubtNotFound)?;
        let exists = record.hypotheses.iter().any(|h| h.id == choice_id);
        if !exists {
            return Err(CortexError::InvalidHypothesisChoice);
        }
        record.chosen_hypothesis_id = Some(choice_id.to_string());
        record.user_justification = Some(justification.to_string());
        record.resolved_certainty = 1.0;
        record.resolved_at_epoch_ms = Some(resolved_epoch_ms);
        record.encrypted_digest = format!(
            "enc:vault:v1:{}:{}:{choice_id}",
            record.context_key, resolved_epoch_ms
        );
        self.memory_store
            .insert(record.context_key.clone(), record.clone());
        Ok(record)
    }

    #[must_use]
    pub fn lookup_prior(&self, context_key: &str) -> Option<&EpistemicConfrontationRecord> {
        self.memory_store.get(context_key)
    }

    #[must_use]
    pub fn pending_count(&self) -> usize {
        self.pending.len()
    }

    #[must_use]
    pub fn resolved_count(&self) -> usize {
        self.memory_store.len()
    }

    #[must_use]
    pub fn list_pending(&self) -> Vec<EpistemicConfrontationRecord> {
        self.pending.values().cloned().collect()
    }

    #[must_use]
    pub fn list_resolved(&self) -> Vec<EpistemicConfrontationRecord> {
        self.memory_store.values().cloned().collect()
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used, clippy::float_cmp)]
mod tests {
    use super::*;

    #[test]
    fn test_epistemic_doubt_and_user_resolution() {
        let mut engine = EpistemicDoubtEngine::new(0.5, 0.15);
        let h1 = EpistemicHypothesis {
            id: "hyp_1".to_string(),
            label: "Linear trajectory".to_string(),
            prior_probability: 0.52,
            predicted_outcome: "Low torque".to_string(),
            action_plan: "Execute linear interpolation".to_string(),
        };
        let h2 = EpistemicHypothesis {
            id: "hyp_2".to_string(),
            label: "Curved obstacle avoidance".to_string(),
            prior_probability: 0.48,
            predicted_outcome: "High clearance".to_string(),
            action_plan: "Execute spline motion".to_string(),
        };

        assert!(engine.should_confront(&[h1.clone(), h2.clone()]));

        let conf = engine
            .initiate_confrontation(
                "conf_001".to_string(),
                "motion_sector_4".to_string(),
                vec![h1, h2],
                1000,
            )
            .unwrap();

        assert_eq!(conf.resolved_certainty, 0.0);
        assert_eq!(engine.pending_count(), 1);

        let resolved = engine
            .resolve_confrontation(
                "conf_001",
                "hyp_2",
                "Obstacle confirmed by visual feed",
                2000,
            )
            .unwrap();

        assert_eq!(resolved.resolved_certainty, 1.0);
        assert_eq!(resolved.chosen_hypothesis_id.as_deref(), Some("hyp_2"));
        assert_eq!(engine.pending_count(), 0);
        assert_eq!(engine.resolved_count(), 1);

        let remembered = engine.lookup_prior("motion_sector_4").unwrap();
        assert_eq!(remembered.resolved_certainty, 1.0);
    }
}
