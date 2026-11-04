use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CerebellarForwardModel {
    input_dim: usize,
    granule_dim: usize,
    output_dim: usize,
    granule_weights: Vec<f64>,
    purkinje_weights: Vec<f64>,
    learning_rate: f64,
}

impl CerebellarForwardModel {
    #[must_use]
    pub fn new(input_dim: usize, granule_expansion_factor: usize, output_dim: usize) -> Self {
        let granule_dim = input_dim.saturating_mul(granule_expansion_factor);
        let total_granule_weights = granule_dim.saturating_mul(input_dim);
        let mut granule_weights = Vec::with_capacity(total_granule_weights);
        for i in 0..total_granule_weights {
            let pseudo_rnd = ((i.saturating_mul(1_013_904_223).saturating_add(1_664_525)) % 1000)
                as f64
                / 1000.0
                - 0.5;
            granule_weights.push(pseudo_rnd);
        }

        let total_purkinje_weights = output_dim.saturating_mul(granule_dim);
        let purkinje_weights = vec![0.01; total_purkinje_weights];

        Self {
            input_dim,
            granule_dim,
            output_dim,
            granule_weights,
            purkinje_weights,
            learning_rate: 0.02,
        }
    }

    #[must_use]
    fn expand_granule(&self, input: &[f64]) -> Vec<f64> {
        let mut granule_acts = Vec::with_capacity(self.granule_dim);
        for g in 0..self.granule_dim {
            let mut sum = 0.0;
            for (i, &inp) in input.iter().enumerate().take(self.input_dim) {
                let weight_idx = g.saturating_mul(self.input_dim).saturating_add(i);
                let w = self.granule_weights.get(weight_idx).copied().unwrap_or(0.0);
                sum += inp * w;
            }
            let nonlin = if sum > 0.0 { sum } else { 0.0 };
            granule_acts.push(nonlin);
        }
        granule_acts
    }

    #[must_use]
    pub fn predict_forward(&self, state: &[f64]) -> Vec<f64> {
        let granule_acts = self.expand_granule(state);
        let mut prediction = Vec::with_capacity(self.output_dim);

        for o in 0..self.output_dim {
            let mut sum = 0.0;
            for (g, &act) in granule_acts.iter().enumerate().take(self.granule_dim) {
                let w_idx = o.saturating_mul(self.granule_dim).saturating_add(g);
                let w = self.purkinje_weights.get(w_idx).copied().unwrap_or(0.0);
                sum += act * w;
            }
            prediction.push(sum);
        }
        prediction
    }

    pub fn learn_climbing_fiber_error(&mut self, state: &[f64], actual_next_state: &[f64]) -> f64 {
        let granule_acts = self.expand_granule(state);
        let prediction = self.predict_forward(state);

        let mut total_error_sq = 0.0;
        for o in 0..self.output_dim {
            let actual = actual_next_state.get(o).copied().unwrap_or(0.0);
            let pred_val = prediction.get(o).copied().unwrap_or(0.0);
            let error = actual - pred_val;
            total_error_sq += error * error;

            for (g, &act) in granule_acts.iter().enumerate().take(self.granule_dim) {
                let delta = self.learning_rate * error * act;
                let w_idx = o.saturating_mul(self.granule_dim).saturating_add(g);
                if let Some(w) = self.purkinje_weights.get_mut(w_idx) {
                    *w += delta;
                }
            }
        }

        total_error_sq.sqrt()
    }
}
