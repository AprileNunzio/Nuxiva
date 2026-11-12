use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ActiveInferencePolicy {
    pub policy_id: usize,
    pub candidate_actions: Vec<Vec<f64>>,
    pub expected_free_energy: f64,
    pub pragmatic_value: f64,
    pub epistemic_value: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct UniversalActiveInferenceEngine {
    pub state_mu: Vec<f64>,
    pub precision_matrix: Vec<f64>,
    pub observation_dim: usize,
    pub action_dim: usize,
    pub learning_rate: f64,
    pub sensory_prediction_error: f64,
}

impl UniversalActiveInferenceEngine {
    #[must_use]
    pub fn new(state_dim: usize, observation_dim: usize, action_dim: usize) -> Self {
        let state_mu = vec![0.0; state_dim];
        let total_prec = observation_dim.saturating_mul(observation_dim);
        let mut precision_matrix = vec![0.0; total_prec];
        for i in 0..observation_dim {
            let diag_idx = i.saturating_mul(observation_dim).saturating_add(i);
            if let Some(val) = precision_matrix.get_mut(diag_idx) {
                *val = 1.0;
            }
        }

        Self {
            state_mu,
            precision_matrix,
            observation_dim,
            action_dim,
            learning_rate: 0.05,
            sensory_prediction_error: 0.0,
        }
    }

    #[must_use]
    pub fn generative_observation_mapping(&self, mu: &[f64]) -> Vec<f64> {
        let mut pred = Vec::with_capacity(self.observation_dim);
        for o in 0..self.observation_dim {
            let mut sum = 0.0;
            for (s, &mu_val) in mu.iter().enumerate() {
                let weight = ((s.saturating_add(o.saturating_mul(3))) % 5) as f64 * 0.2 + 0.1;
                sum += mu_val * weight;
            }
            pred.push(sum);
        }
        pred
    }

    pub fn update_variational_free_energy(&mut self, observations: &[f64]) -> f64 {
        let pred_obs = self.generative_observation_mapping(&self.state_mu);
        let mut errors = Vec::with_capacity(self.observation_dim);
        let mut vfe = 0.0;

        for (i, pred_val) in pred_obs.iter().enumerate().take(self.observation_dim) {
            let obs_val = observations.get(i).copied().unwrap_or(0.0);
            let err = obs_val - *pred_val;
            errors.push(err);

            let diag_idx = i.saturating_mul(self.observation_dim).saturating_add(i);
            let prec = self.precision_matrix.get(diag_idx).copied().unwrap_or(1.0);
            vfe += 0.5 * prec * err * err;
        }

        for (s, mu_val) in self.state_mu.iter_mut().enumerate() {
            let mut gradient = 0.0;
            for (o, &err) in errors.iter().enumerate().take(self.observation_dim) {
                let weight = ((s.saturating_add(o.saturating_mul(3))) % 5) as f64 * 0.2 + 0.1;
                let diag_idx = o.saturating_mul(self.observation_dim).saturating_add(o);
                let prec = self.precision_matrix.get(diag_idx).copied().unwrap_or(1.0);
                gradient += err * prec * weight;
            }
            *mu_val += self.learning_rate * gradient;
        }

        self.sensory_prediction_error = vfe;
        vfe
    }

    #[must_use]
    pub fn plan_expected_free_energy(
        &self,
        candidate_policies: &[Vec<Vec<f64>>],
        target_preferences: &[f64],
    ) -> Option<ActiveInferencePolicy> {
        if candidate_policies.is_empty() {
            return None;
        }

        let mut scored_policies = Vec::new();

        for (p_idx, policy) in candidate_policies.iter().enumerate() {
            let mut sim_mu = self.state_mu.clone();
            let mut total_efe = 0.0;
            let mut pragmatic_sum = 0.0;
            let mut epistemic_sum = 0.0;

            for action in policy {
                for (s, mu_val) in sim_mu.iter_mut().enumerate() {
                    let act_contrib = action.get(s).copied().unwrap_or(0.0);
                    *mu_val += 0.1 * act_contrib;
                }

                let predicted_obs = self.generative_observation_mapping(&sim_mu);
                let mut dist_to_target = 0.0;
                for (o, &pred_val) in predicted_obs.iter().enumerate().take(self.observation_dim) {
                    let target = target_preferences.get(o).copied().unwrap_or(0.0);
                    let diff = target - pred_val;
                    dist_to_target += diff * diff;
                }
                let pragmatic = dist_to_target.sqrt();

                let mut novelty = 0.0;
                for &val in &sim_mu {
                    novelty += val.abs();
                }
                let epistemic = (1.0 / (1.0 + novelty)).clamp(0.0, 1.0);

                let efe = pragmatic - 0.3 * epistemic;
                total_efe += efe;
                pragmatic_sum += pragmatic;
                epistemic_sum += epistemic;
            }

            scored_policies.push(ActiveInferencePolicy {
                policy_id: p_idx,
                candidate_actions: policy.clone(),
                expected_free_energy: total_efe,
                pragmatic_value: pragmatic_sum,
                epistemic_value: epistemic_sum,
            });
        }

        scored_policies.sort_by(|a, b| {
            a.expected_free_energy
                .partial_cmp(&b.expected_free_energy)
                .unwrap_or(std::cmp::Ordering::Equal)
        });

        scored_policies.into_iter().next()
    }
}
