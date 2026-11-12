use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CalibrationBin {
    pub total_samples: usize,
    pub correct_samples: usize,
    pub confidence_sum: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SecondOrderMetacognition {
    bins: Vec<CalibrationBin>,
    min_operational_competence: f64,
}

impl Default for SecondOrderMetacognition {
    fn default() -> Self {
        Self::new(10, 0.70)
    }
}

impl SecondOrderMetacognition {
    #[must_use]
    pub fn new(num_bins: usize, min_operational_competence: f64) -> Self {
        let mut bins = Vec::with_capacity(num_bins);
        for _ in 0..num_bins {
            bins.push(CalibrationBin {
                total_samples: 0,
                correct_samples: 0,
                confidence_sum: 0.0,
            });
        }
        Self {
            bins,
            min_operational_competence,
        }
    }

    pub fn record_prediction(&mut self, confidence: f64, was_correct: bool) {
        let conf = confidence.clamp(0.0, 1.0);
        let max_idx = self.bins.len().saturating_sub(1);
        let bin_idx = ((conf * self.bins.len() as f64).floor() as usize).min(max_idx);
        if let Some(bin) = self.bins.get_mut(bin_idx) {
            bin.total_samples = bin.total_samples.saturating_add(1);
            bin.confidence_sum += conf;
            if was_correct {
                bin.correct_samples = bin.correct_samples.saturating_add(1);
            }
        }
    }

    #[must_use]
    pub fn expected_calibration_error(&self) -> f64 {
        let mut grand_total: usize = 0;
        for b in &self.bins {
            grand_total = grand_total.saturating_add(b.total_samples);
        }
        if grand_total == 0 {
            return 0.0;
        }

        let mut ece = 0.0;
        for bin in &self.bins {
            if bin.total_samples > 0 {
                let acc = bin.correct_samples as f64 / bin.total_samples as f64;
                let conf = bin.confidence_sum / bin.total_samples as f64;
                let weight = bin.total_samples as f64 / grand_total as f64;
                ece += weight * (acc - conf).abs();
            }
        }
        ece
    }

    #[must_use]
    pub fn decompose_uncertainty(&self, model_variance: f64, observation_noise: f64) -> (f64, f64) {
        let epistemic = model_variance.clamp(0.0, 1.0);
        let aleatoric = observation_noise.clamp(0.0, 1.0);
        (epistemic, aleatoric)
    }

    #[must_use]
    pub fn should_refuse_or_verify(
        &self,
        estimated_competence: f64,
        epistemic_uncertainty: f64,
    ) -> bool {
        let effective_security = estimated_competence * (1.0 - epistemic_uncertainty);
        effective_security < self.min_operational_competence
    }
}
