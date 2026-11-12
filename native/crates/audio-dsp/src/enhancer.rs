use serde::{Deserialize, Serialize};

const MAX_GAIN: f32 = 8.0;
const GATE_ATTENUATION: f32 = 0.15;
const EPSILON: f64 = 1e-9;

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct AcousticFeatures {
    pub zero_crossing_rate: f64,
    pub energy: f64,
    pub crest_factor: f64,
    pub clarity_score: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EnhancedSignal {
    pub samples: Vec<f32>,
    pub original_rms: f64,
    pub enhanced_rms: f64,
    pub snr_gain_db: f64,
    pub features: Option<AcousticFeatures>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct SignalEnhancer {
    target_peak: f32,
    noise_floor_ratio: f32,
}

impl Default for SignalEnhancer {
    fn default() -> Self {
        Self::new(0.85, 0.08)
    }
}

#[allow(clippy::cast_precision_loss)]
fn mean_of(sum: f64, count: usize) -> f64 {
    if count == 0 { 0.0 } else { sum / count as f64 }
}

#[must_use]
pub fn rms(signal: &[f32]) -> f64 {
    let sum: f64 = signal.iter().map(|x| f64::from(*x) * f64::from(*x)).sum();
    mean_of(sum, signal.len()).sqrt()
}

#[must_use]
pub fn peak(signal: &[f32]) -> f32 {
    signal.iter().fold(0.0_f32, |acc, x| acc.max(x.abs()))
}

fn sign(value: f32) -> f32 {
    if value > 0.0 {
        1.0
    } else if value < 0.0 {
        -1.0
    } else {
        0.0
    }
}

#[must_use]
pub fn acoustic_features(signal: &[f32]) -> Option<AcousticFeatures> {
    if signal.is_empty() {
        return None;
    }
    let crossings: f64 = signal
        .windows(2)
        .map(|pair| match pair {
            [a, b] => f64::from((sign(*b) - sign(*a)).abs()),
            _ => 0.0,
        })
        .sum();
    let zcr = mean_of(crossings, signal.len().saturating_sub(1)) / 2.0;
    let energy: f64 = signal.iter().map(|x| f64::from(*x) * f64::from(*x)).sum();
    let crest = f64::from(peak(signal)) / (rms(signal) + EPSILON);
    Some(AcousticFeatures {
        zero_crossing_rate: zcr,
        energy,
        crest_factor: crest,
        clarity_score: zcr.mul_add(-1.5, 1.0).clamp(0.1, 1.0),
    })
}

impl SignalEnhancer {
    #[must_use]
    pub fn new(target_peak: f32, noise_floor_ratio: f32) -> Self {
        Self {
            target_peak: if target_peak.is_finite() {
                target_peak.clamp(0.01, 1.0)
            } else {
                0.85
            },
            noise_floor_ratio: if noise_floor_ratio.is_finite() {
                noise_floor_ratio.clamp(0.0, 1.0)
            } else {
                0.08
            },
        }
    }

    fn spectral_gate(&self, signal: &[f32]) -> Vec<f32> {
        let mean_abs: f64 = signal.iter().map(|x| f64::from(x.abs())).sum();
        #[allow(clippy::cast_possible_truncation)]
        let threshold =
            (mean_of(mean_abs, signal.len()) * f64::from(self.noise_floor_ratio)) as f32;
        signal
            .iter()
            .map(|x| {
                if x.abs() > threshold {
                    *x
                } else {
                    x * GATE_ATTENUATION
                }
            })
            .collect()
    }

    fn automatic_gain(&self, signal: Vec<f32>) -> Vec<f32> {
        let loudest = peak(&signal);
        if loudest < 1e-6 {
            return signal;
        }
        let gain = (self.target_peak / loudest).min(MAX_GAIN);
        signal.into_iter().map(|x| x * gain).collect()
    }

    #[must_use]
    pub fn enhance(&self, signal: &[f32]) -> EnhancedSignal {
        if signal.is_empty() {
            return EnhancedSignal {
                samples: Vec::new(),
                original_rms: 0.0,
                enhanced_rms: 0.0,
                snr_gain_db: 0.0,
                features: None,
            };
        }
        let original_rms = rms(signal) + EPSILON;
        let amplified = self.automatic_gain(self.spectral_gate(signal));
        let enhanced_rms = rms(&amplified) + EPSILON;
        let features = acoustic_features(&amplified);
        EnhancedSignal {
            snr_gain_db: 20.0 * (enhanced_rms / original_rms).log10(),
            samples: amplified,
            original_rms,
            enhanced_rms,
            features,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_signal_is_neutral() {
        let out = SignalEnhancer::default().enhance(&[]);
        assert!(out.samples.is_empty());
        assert!(out.features.is_none());
    }

    #[test]
    fn quiet_signal_is_amplified_up_to_target() {
        let signal: Vec<f32> = (0..320)
            .map(|i| if i % 2 == 0 { 0.2 } else { -0.2 })
            .collect();
        let out = SignalEnhancer::default().enhance(&signal);
        assert!((peak(&out.samples) - 0.85).abs() < 1e-4);
        assert!(out.snr_gain_db > 0.0);
    }

    #[test]
    fn gain_is_capped() {
        let signal = vec![0.001_f32; 64];
        let out = SignalEnhancer::default().enhance(&signal);
        assert!((peak(&out.samples) - 0.008).abs() < 1e-5);
    }

    #[test]
    fn alternating_signal_has_full_zero_crossing() {
        let signal: Vec<f32> = (0..100)
            .map(|i| if i % 2 == 0 { 0.5 } else { -0.5 })
            .collect();
        let features = acoustic_features(&signal);
        assert!(features.is_some_and(|f| (f.zero_crossing_rate - 1.0).abs() < 1e-9));
    }

    #[test]
    fn invalid_parameters_fall_back() {
        let enhancer = SignalEnhancer::new(f32::NAN, f32::INFINITY);
        assert_eq!(enhancer, SignalEnhancer::default());
    }
}
