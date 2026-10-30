use crate::enhancer::rms;
use serde::{Deserialize, Serialize};

const DEFAULT_PITCH_HZ: f64 = 140.0;
const DEFAULT_PITCH_STD: f64 = 12.0;
const SILENCE_LEVEL: f32 = 0.02;

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct VoiceBiomarkers {
    pub pitch_f0_mean_hz: f64,
    pub pitch_variability_st: f64,
    pub jitter_percent: f64,
    pub shimmer_percent: f64,
    pub monotone_score: f64,
    pub vocal_energy_rms: f64,
    pub speech_pause_ratio: f64,
    pub depressive_vocal_indicator: f64,
}

impl Default for VoiceBiomarkers {
    fn default() -> Self {
        Self {
            pitch_f0_mean_hz: 140.0,
            pitch_variability_st: 15.0,
            jitter_percent: 0.8,
            shimmer_percent: 2.2,
            monotone_score: 0.25,
            vocal_energy_rms: 0.15,
            speech_pause_ratio: 0.15,
            depressive_vocal_indicator: 0.15,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct VoiceBiomarkerAnalyzer {
    sample_rate: u32,
}

impl Default for VoiceBiomarkerAnalyzer {
    fn default() -> Self {
        Self::new(16_000)
    }
}

#[allow(clippy::cast_precision_loss)]
fn as_f64(value: usize) -> f64 {
    value as f64
}

fn population_std(values: &[f64]) -> f64 {
    if values.is_empty() {
        return 0.0;
    }
    let count = as_f64(values.len());
    let mean = values.iter().sum::<f64>() / count;
    (values.iter().map(|v| (v - mean) * (v - mean)).sum::<f64>() / count).sqrt()
}

fn autocorrelation(signal: &[f32], lag: usize) -> f64 {
    signal
        .iter()
        .zip(signal.iter().skip(lag))
        .map(|(a, b)| f64::from(*a) * f64::from(*b))
        .sum()
}

impl VoiceBiomarkerAnalyzer {
    #[must_use]
    pub fn new(sample_rate: u32) -> Self {
        Self {
            sample_rate: sample_rate.clamp(4_000, 192_000),
        }
    }

    #[must_use]
    pub fn estimate_pitch(&self, signal: &[f32]) -> (f64, f64) {
        let rate = f64::from(self.sample_rate);
        let min_lag = usize::try_from((self.sample_rate / 400).max(1)).unwrap_or(usize::MAX);
        let max_lag = usize::try_from(self.sample_rate / 60)
            .unwrap_or(usize::MAX)
            .min(signal.len().saturating_sub(1));
        if min_lag >= max_lag {
            return (DEFAULT_PITCH_HZ, DEFAULT_PITCH_STD);
        }
        let mut best_lag = min_lag;
        let mut best = f64::NEG_INFINITY;
        for lag in min_lag..max_lag {
            let value = autocorrelation(signal, lag);
            if value > best {
                best = value;
                best_lag = lag;
            }
        }
        let f0 = rate / as_f64(best_lag);
        let frame = usize::try_from(self.sample_rate / 20).unwrap_or(1).max(1);
        let energies: Vec<f64> = if signal.len() < frame {
            vec![population_std(
                &signal.iter().map(|x| f64::from(*x)).collect::<Vec<_>>(),
            )]
        } else {
            signal
                .chunks_exact(frame)
                .map(|chunk| {
                    population_std(&chunk.iter().map(|x| f64::from(*x)).collect::<Vec<_>>())
                })
                .collect()
        };
        let variability = (population_std(&energies) * 100.0).min(45.0);
        (f0.clamp(65.0, 380.0), variability)
    }

    #[must_use]
    pub fn extract(&self, signal: &[f32]) -> VoiceBiomarkers {
        if signal.is_empty() {
            return VoiceBiomarkers::default();
        }
        let energy = rms(signal) + 1e-9;
        let (pitch, pitch_std) = self.estimate_pitch(signal);
        let monotone = (1.0 - pitch_std / 35.0).clamp(0.0, 1.0);
        let silent = signal.iter().filter(|x| x.abs() < SILENCE_LEVEL).count();
        let silence_ratio = as_f64(silent) / as_f64(signal.len());
        let depressive =
            monotone * 0.45 + silence_ratio * 0.35 + (1.0 - energy * 5.0).max(0.0) * 0.20;
        VoiceBiomarkers {
            pitch_f0_mean_hz: pitch,
            pitch_variability_st: pitch_std,
            jitter_percent: (pitch_std * 0.08).clamp(0.2, 5.0),
            shimmer_percent: (silence_ratio * 4.0).clamp(0.5, 12.0),
            monotone_score: monotone,
            vocal_energy_rms: energy,
            speech_pause_ratio: silence_ratio,
            depressive_vocal_indicator: depressive.clamp(0.0, 1.0),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sine(freq: f64, rate: f64, count: usize, amplitude: f64) -> Vec<f32> {
        (0..count)
            .map(|i| {
                #[allow(clippy::cast_possible_truncation)]
                let value = ((2.0 * std::f64::consts::PI * freq * as_f64(i) / rate).sin()
                    * amplitude) as f32;
                value
            })
            .collect()
    }

    #[test]
    fn detects_pitch_of_pure_tone() {
        let analyzer = VoiceBiomarkerAnalyzer::default();
        let (f0, _) = analyzer.estimate_pitch(&sine(200.0, 16_000.0, 16_000, 0.5));
        assert!((f0 - 200.0).abs() < 2.0);
    }

    #[test]
    fn silence_is_monotone_and_paused() {
        let bio = VoiceBiomarkerAnalyzer::default().extract(&vec![0.0; 8_000]);
        assert!((bio.speech_pause_ratio - 1.0).abs() < f64::EPSILON);
        assert!(bio.depressive_vocal_indicator > 0.9);
    }

    #[test]
    fn empty_signal_returns_defaults() {
        assert_eq!(
            VoiceBiomarkerAnalyzer::default().extract(&[]),
            VoiceBiomarkers::default()
        );
    }

    #[test]
    fn short_signal_uses_default_pitch() {
        let (f0, std) = VoiceBiomarkerAnalyzer::default().estimate_pitch(&[0.1; 20]);
        assert!((f0 - DEFAULT_PITCH_HZ).abs() < f64::EPSILON);
        assert!((std - DEFAULT_PITCH_STD).abs() < f64::EPSILON);
    }
}
