use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct IntrinsicCuriosityEngine {
    pub exploration_bonus_weight: f64,
    pub empowerment_weight: f64,
}

impl Default for IntrinsicCuriosityEngine {
    fn default() -> Self {
        Self {
            exploration_bonus_weight: 1.0,
            empowerment_weight: 0.8,
        }
    }
}

impl IntrinsicCuriosityEngine {
    #[must_use]
    pub fn new(exploration_weight: f64, empowerment_weight: f64) -> Self {
        Self {
            exploration_bonus_weight: exploration_weight,
            empowerment_weight,
        }
    }

    #[must_use]
    pub fn compute_information_gain(&self, prior_entropy: f64, posterior_entropy: f64) -> f64 {
        (prior_entropy - posterior_entropy).max(0.0) * self.exploration_bonus_weight
    }

    #[must_use]
    pub fn compute_empowerment(&self, action_count: usize, reachable_states_entropy: f64) -> f64 {
        let max_action_entropy = (action_count as f64).ln().max(1e-6);
        (reachable_states_entropy / max_action_entropy).clamp(0.0, 1.0) * self.empowerment_weight
    }

    #[must_use]
    pub fn evaluate_curiosity_reward(
        &self,
        prior_entropy: f64,
        posterior_entropy: f64,
        action_count: usize,
        reachable_states_entropy: f64,
    ) -> f64 {
        let ig = self.compute_information_gain(prior_entropy, posterior_entropy);
        let emp = self.compute_empowerment(action_count, reachable_states_entropy);
        ig + emp
    }
}
