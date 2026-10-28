use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct NeuromodulatorState {
    pub dopamine_rpe: f64,
    pub noradrenaline_surprise: f64,
    pub acetylcholine_precision: f64,
    pub serotonin_patience: f64,
}

impl Default for NeuromodulatorState {
    fn default() -> Self {
        Self {
            dopamine_rpe: 0.0,
            noradrenaline_surprise: 0.1,
            acetylcholine_precision: 0.8,
            serotonin_patience: 0.9,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct NeuromodulatoryBus {
    state: NeuromodulatorState,
    decay_rate: f64,
}

impl Default for NeuromodulatoryBus {
    fn default() -> Self {
        Self::new()
    }
}

impl NeuromodulatoryBus {
    #[must_use]
    pub fn new() -> Self {
        Self {
            state: NeuromodulatorState::default(),
            decay_rate: 0.05,
        }
    }

    #[must_use]
    pub fn state(&self) -> &NeuromodulatorState {
        &self.state
    }

    pub fn emit_dopamine_rpe(&mut self, reward: f64, next_value: f64, current_value: f64) {
        let gamma = self.effective_discount_factor();
        let delta_rpe = reward + gamma * next_value - current_value;
        self.state.dopamine_rpe =
            (self.state.dopamine_rpe * 0.7 + delta_rpe * 0.3).clamp(-2.0, 2.0);
    }

    pub fn emit_noradrenaline_surprise(&mut self, prediction_divergence: f64) {
        self.state.noradrenaline_surprise =
            (self.state.noradrenaline_surprise * 0.6 + prediction_divergence * 0.4).clamp(0.0, 2.0);
    }

    pub fn update_acetylcholine(&mut self, known_channel_noise: f64) {
        let precision = (1.0 / (1.0 + known_channel_noise)).clamp(0.1, 1.0);
        self.state.acetylcholine_precision =
            (self.state.acetylcholine_precision * 0.8 + precision * 0.2).clamp(0.1, 1.0);
    }

    pub fn update_serotonin(&mut self, aversive_punishment: f64) {
        let suppression = (1.0 - aversive_punishment.clamp(0.0, 0.8)).clamp(0.2, 1.0);
        self.state.serotonin_patience =
            (self.state.serotonin_patience * 0.9 + suppression * 0.1).clamp(0.2, 1.0);
    }

    pub fn step_decay(&mut self) {
        self.state.dopamine_rpe *= 1.0 - self.decay_rate;
        self.state.noradrenaline_surprise =
            0.1 + (self.state.noradrenaline_surprise - 0.1) * (1.0 - self.decay_rate);
    }

    #[must_use]
    pub fn effective_discount_factor(&self) -> f64 {
        (0.85 + 0.14 * self.state.serotonin_patience).clamp(0.85, 0.99)
    }

    #[must_use]
    pub fn requires_cortical_context_reset(&self) -> bool {
        self.state.noradrenaline_surprise > 1.2
    }
}
