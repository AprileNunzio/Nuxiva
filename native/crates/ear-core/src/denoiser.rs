use std::f32::consts::FRAC_PI_2;

use crate::gain::omlsa_gain;
use crate::noise::Mcra;
use crate::stft::{BINS, HOP, N_FFT, Spectrum, Stft, bin_hz};

const ALPHA_DD: f32 = 0.9;
const XI_MIN: f32 = 0.003_162;
const GAMMA_MAX: f32 = 1e4;
const HIGHPASS_MAX: f32 = 300.0;
const FLOOR_MIN: f32 = 0.05;

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct DenoiserConfig {
    pub highpass_hz: f32,
    pub suppress: bool,
    pub floor: f32,
}

impl Default for DenoiserConfig {
    fn default() -> Self {
        Self {
            highpass_hz: 90.0,
            suppress: true,
            floor: 0.15,
        }
    }
}

impl DenoiserConfig {
    #[must_use]
    pub fn sanitized(self) -> Self {
        let highpass_hz = if self.highpass_hz.is_finite() {
            self.highpass_hz.clamp(0.0, HIGHPASS_MAX)
        } else {
            0.0
        };
        let floor = if self.floor.is_finite() {
            self.floor.clamp(FLOOR_MIN, 1.0)
        } else {
            0.15
        };
        Self {
            highpass_hz,
            suppress: self.suppress,
            floor,
        }
    }

    #[must_use]
    pub fn enabled(&self) -> bool {
        self.highpass_hz > 0.0 || self.suppress
    }
}

fn highpass_curve(cutoff: f32) -> Vec<f32> {
    (0..BINS)
        .map(|k| {
            if cutoff <= 0.0 {
                return 1.0;
            }
            let half = cutoff * 0.5;
            let ramp = ((bin_hz(k) - half) / half).clamp(0.0, 1.0);
            (ramp * FRAC_PI_2).sin().powi(2)
        })
        .collect()
}

#[derive(Debug)]
pub struct Denoiser {
    config: DenoiserConfig,
    stft: Stft,
    highpass: Vec<f32>,
    mcra: Mcra,
    prev_gain: Vec<f32>,
    prev_gamma: Vec<f32>,
    gain: Vec<f32>,
    power: Vec<f32>,
    pending: Vec<f32>,
    overlap: Vec<f32>,
    spectrum: Spectrum,
}

impl Denoiser {
    #[must_use]
    pub fn new(config: DenoiserConfig) -> Self {
        let config = config.sanitized();
        Self {
            highpass: highpass_curve(config.highpass_hz),
            config,
            stft: Stft::new(),
            mcra: Mcra::new(),
            prev_gain: vec![1.0; BINS],
            prev_gamma: vec![1.0; BINS],
            gain: vec![1.0; BINS],
            power: vec![0.0; BINS],
            pending: Vec::with_capacity(N_FFT.saturating_mul(4)),
            overlap: vec![0.0; HOP],
            spectrum: Stft::empty_spectrum(),
        }
    }

    #[must_use]
    pub fn config(&self) -> DenoiserConfig {
        self.config
    }

    #[must_use]
    pub fn noise(&self) -> &[f32] {
        self.mcra.noise()
    }

    #[must_use]
    pub fn pending(&self) -> usize {
        self.pending.len()
    }

    pub fn seed(&mut self, psd: &[f32]) -> bool {
        self.mcra.seed(psd)
    }

    pub fn restart(&mut self) {
        self.pending.clear();
        self.overlap.iter_mut().for_each(|v| *v = 0.0);
        self.prev_gain.iter_mut().for_each(|v| *v = 1.0);
        self.prev_gamma.iter_mut().for_each(|v| *v = 1.0);
    }

    fn compute_gain(&mut self) {
        for (p, c) in self.power.iter_mut().zip(&self.spectrum) {
            *p = c.norm_sqr();
        }
        if !self.config.suppress {
            self.gain.clone_from(&self.highpass);
            return;
        }
        self.mcra.update(&self.power);
        let floor = self.config.floor;
        for ((((g, hp), y), noise), ((pg, pgm), presence)) in self
            .gain
            .iter_mut()
            .zip(&self.highpass)
            .zip(&self.power)
            .zip(self.mcra.noise())
            .zip(
                self.prev_gain
                    .iter_mut()
                    .zip(self.prev_gamma.iter_mut())
                    .zip(self.mcra.presence()),
            )
        {
            let gamma = (y / noise.max(1e-12)).clamp(0.0, GAMMA_MAX);
            let xi = (ALPHA_DD * *pg * *pg * *pgm + (1.0 - ALPHA_DD) * (gamma - 1.0).max(0.0))
                .max(XI_MIN);
            let value = omlsa_gain(xi, gamma, 1.0 - presence, floor);
            *pg = value;
            *pgm = gamma;
            *g = hp * value;
        }
    }

    pub fn process(&mut self, input: &[f32], out: &mut Vec<f32>) {
        if !self.config.enabled() {
            out.extend_from_slice(input);
            return;
        }
        self.pending
            .extend(input.iter().map(|v| if v.is_finite() { *v } else { 0.0 }));
        let mut start = 0_usize;
        while self.pending.len().saturating_sub(start) >= N_FFT {
            let end = start.saturating_add(N_FFT);
            let Some(frame) = self.pending.get(start..end) else {
                break;
            };
            if !self.stft.analyze(frame, &mut self.spectrum) {
                break;
            }
            self.compute_gain();
            for (c, g) in self.spectrum.iter_mut().zip(&self.gain) {
                *c = realfft::num_complex::Complex32::new(c.re * g, c.im * g);
            }
            let Some(synth) = self.stft.synthesize(&mut self.spectrum) else {
                break;
            };
            let (head, tail) = synth.split_at(HOP);
            out.extend(self.overlap.iter().zip(head).map(|(a, b)| a + b));
            self.overlap.copy_from_slice(tail);
            start = start.saturating_add(HOP);
        }
        self.pending.drain(..start.min(self.pending.len()));
    }
}

#[must_use]
pub fn clean_utterance(samples: &[f32], noise: Option<&[f32]>, config: DenoiserConfig) -> Vec<f32> {
    let mut denoiser = Denoiser::new(config);
    if !denoiser.config().enabled() {
        return samples.to_vec();
    }
    if let Some(psd) = noise {
        let _ = denoiser.seed(psd);
    }
    let mut padded = Vec::with_capacity(samples.len().saturating_add(HOP).saturating_add(N_FFT));
    padded.resize(HOP, 0.0);
    padded.extend_from_slice(samples);
    padded.resize(padded.len().saturating_add(N_FFT), 0.0);
    let mut out = Vec::with_capacity(padded.len());
    denoiser.process(&padded, &mut out);
    let mut result: Vec<f32> = out.into_iter().skip(HOP).take(samples.len()).collect();
    result.resize(samples.len(), 0.0);
    result
}
