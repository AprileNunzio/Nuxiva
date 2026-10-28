use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ThalamicChannel {
    pub channel_id: String,
    pub attentional_gain: f64,
    pub oscillation_phase: f64,
    pub oscillation_frequency_hz: f64,
    pub pulvinar_coupling_weight: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ThalamicRelay {
    pub channels: Vec<ThalamicChannel>,
    pub master_clock_phase: f64,
}

impl Default for ThalamicRelay {
    fn default() -> Self {
        Self::new()
    }
}

impl ThalamicRelay {
    #[must_use]
    pub fn new() -> Self {
        Self {
            channels: Vec::new(),
            master_clock_phase: 0.0,
        }
    }

    pub fn register_channel(
        &mut self,
        channel_id: &str,
        frequency_hz: f64,
        pulvinar_coupling_weight: f64,
    ) {
        self.channels.push(ThalamicChannel {
            channel_id: channel_id.to_string(),
            attentional_gain: 1.0,
            oscillation_phase: 0.0,
            oscillation_frequency_hz: frequency_hz,
            pulvinar_coupling_weight,
        });
    }

    pub fn set_attention(&mut self, channel_id: &str, gain: f64) {
        if let Some(ch) = self
            .channels
            .iter_mut()
            .find(|c| c.channel_id == channel_id)
        {
            ch.attentional_gain = gain.clamp(0.0, 5.0);
        }
    }

    pub fn step(&mut self, dt_seconds: f64) {
        self.master_clock_phase = (self.master_clock_phase
            + 2.0 * std::f64::consts::PI * 10.0 * dt_seconds)
            % (2.0 * std::f64::consts::PI);

        for ch in &mut self.channels {
            let omega = 2.0 * std::f64::consts::PI * ch.oscillation_frequency_hz;
            ch.oscillation_phase =
                (ch.oscillation_phase + omega * dt_seconds) % (2.0 * std::f64::consts::PI);
        }
    }

    #[must_use]
    pub fn gate_signal(&self, channel_id: &str, signal: &[f64]) -> Vec<f64> {
        let ch = self.channels.iter().find(|c| c.channel_id == channel_id);
        let (gain, phase, coupling) = match ch {
            Some(c) => (
                c.attentional_gain,
                c.oscillation_phase,
                c.pulvinar_coupling_weight,
            ),
            None => (1.0, 0.0, 0.5),
        };

        let phase_coherence = ((phase - self.master_clock_phase).cos() + 1.0) * 0.5;
        let effective_gain = gain * (1.0 + coupling * (phase_coherence - 0.5));

        signal.iter().map(|&x| x * effective_gain).collect()
    }
}
