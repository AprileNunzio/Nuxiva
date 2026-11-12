use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RStdpConfig {
    pub learning_rate: f64,
    pub tau_plus: f64,
    pub tau_minus: f64,
    pub a_plus: f64,
    pub a_minus: f64,
    pub tau_eligibility: f64,
    pub w_min: f64,
    pub w_max: f64,
}

impl Default for RStdpConfig {
    fn default() -> Self {
        Self {
            learning_rate: 0.05,
            tau_plus: 20.0,
            tau_minus: 20.0,
            a_plus: 1.0,
            a_minus: 1.2,
            tau_eligibility: 50.0,
            w_min: 0.0,
            w_max: 1.0,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RewardModulatedStdpSynapse {
    pub weight: f64,
    pub eligibility_trace: f64,
    pub last_pre_spike_time: Option<f64>,
    pub last_post_spike_time: Option<f64>,
    config: RStdpConfig,
}

impl Default for RewardModulatedStdpSynapse {
    fn default() -> Self {
        Self::new(0.5, RStdpConfig::default())
    }
}

impl RewardModulatedStdpSynapse {
    #[must_use]
    pub fn new(initial_weight: f64, config: RStdpConfig) -> Self {
        Self {
            weight: initial_weight.clamp(config.w_min, config.w_max),
            eligibility_trace: 0.0,
            last_pre_spike_time: None,
            last_post_spike_time: None,
            config,
        }
    }

    pub fn on_pre_spike(&mut self, current_time: f64) {
        self.last_pre_spike_time = Some(current_time);
        if let Some(post_time) = self.last_post_spike_time {
            let dt = post_time - current_time;
            if dt < 0.0 {
                let ltd = -self.config.a_minus * (dt / self.config.tau_minus).exp();
                self.eligibility_trace += ltd;
            }
        }
    }

    pub fn on_post_spike(&mut self, current_time: f64) {
        self.last_post_spike_time = Some(current_time);
        if let Some(pre_time) = self.last_pre_spike_time {
            let dt = current_time - pre_time;
            if dt > 0.0 {
                let ltp = self.config.a_plus * (-dt / self.config.tau_plus).exp();
                self.eligibility_trace += ltp;
            }
        }
    }

    pub fn step_decay_and_modulate(&mut self, dt_ms: f64, dopamine_rpe: f64) {
        let decay = (-dt_ms / self.config.tau_eligibility).exp();
        self.eligibility_trace *= decay;

        let delta_w = self.config.learning_rate * dopamine_rpe * self.eligibility_trace;
        self.weight = (self.weight + delta_w).clamp(self.config.w_min, self.config.w_max);
    }
}
