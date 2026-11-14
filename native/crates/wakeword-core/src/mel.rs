#![allow(clippy::indexing_slicing, clippy::arithmetic_side_effects)]

use std::f32::consts::PI;
use std::fmt;
use std::sync::Arc;

use realfft::num_complex::Complex32;
use realfft::{RealFftPlanner, RealToComplex};

pub const RATE: usize = 16_000;
pub const WIN: usize = 400;
pub const HOP: usize = 160;
pub const CEPS: usize = 12;
pub const DIM: usize = CEPS * 2;

const N_FFT: usize = 512;
const BINS: usize = N_FFT / 2 + 1;
const MEL: usize = 40;
const LOW_HZ: f32 = 80.0;
const HIGH_HZ: f32 = 7600.0;
const PREEMPHASIS: f32 = 0.97;
const DELTA_WEIGHT: f32 = 0.5;
const FLOOR: f32 = 1e-10;
const DCT_SCALE: f32 = 0.2236068;

pub type Ceps = [f32; CEPS];
pub type Feat = [f32; DIM];

#[derive(Debug, Clone, Copy)]
pub struct Frame {
    pub ceps: Ceps,
    pub energy_db: f32,
}

type Band = Vec<(usize, f32)>;

pub struct Frontend {
    plan: Arc<dyn RealToComplex<f32>>,
    window: Vec<f32>,
    bank: Vec<Band>,
    dct: Vec<[f32; MEL]>,
    input: Vec<f32>,
    spectrum: Vec<Complex32>,
    scratch: Vec<Complex32>,
}

impl fmt::Debug for Frontend {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Frontend").field("n_fft", &N_FFT).finish()
    }
}

impl Default for Frontend {
    fn default() -> Self {
        Self::new()
    }
}

fn hz_to_mel(hz: f32) -> f32 {
    2595.0 * (1.0 + hz / 700.0).log10()
}

fn mel_to_hz(mel: f32) -> f32 {
    700.0 * (10f32.powf(mel / 2595.0) - 1.0)
}

fn filterbank() -> Vec<Band> {
    let low = hz_to_mel(LOW_HZ);
    let high = hz_to_mel(HIGH_HZ);
    let edges: Vec<f32> = (0..MEL + 2)
        .map(|i| mel_to_hz(low + (high - low) * i as f32 / (MEL + 1) as f32))
        .collect();
    let bin_hz = RATE as f32 / N_FFT as f32;
    (0..MEL)
        .map(|m| {
            let (a, b, c) = (edges[m], edges[m + 1], edges[m + 2]);
            (0..BINS)
                .filter_map(|bin| {
                    let hz = bin as f32 * bin_hz;
                    let w = if hz > a && hz <= b {
                        (hz - a) / (b - a)
                    } else if hz > b && hz < c {
                        (c - hz) / (c - b)
                    } else {
                        0.0
                    };
                    (w > 0.0).then_some((bin, w))
                })
                .collect()
        })
        .collect()
}

fn dct_matrix() -> Vec<[f32; MEL]> {
    (1..=CEPS)
        .map(|k| {
            let mut row = [0.0f32; MEL];
            for (n, cell) in row.iter_mut().enumerate() {
                *cell = (PI * k as f32 * (n as f32 + 0.5) / MEL as f32).cos();
            }
            row
        })
        .collect()
}

fn hann() -> Vec<f32> {
    (0..WIN)
        .map(|i| 0.5 - 0.5 * (2.0 * PI * i as f32 / (WIN - 1) as f32).cos())
        .collect()
}

impl Frontend {
    #[must_use]
    pub fn new() -> Self {
        let mut planner = RealFftPlanner::<f32>::new();
        let plan = planner.plan_fft_forward(N_FFT);
        let spectrum = plan.make_output_vec();
        let scratch = plan.make_scratch_vec();
        Self {
            plan,
            window: hann(),
            bank: filterbank(),
            dct: dct_matrix(),
            input: vec![0.0; N_FFT],
            spectrum,
            scratch,
        }
    }

    pub fn frame(&mut self, samples: &[f32]) -> Option<Frame> {
        if samples.len() != WIN || samples.iter().any(|s| !s.is_finite()) {
            return None;
        }
        let power = samples.iter().map(|s| s * s).sum::<f32>() / WIN as f32;
        self.input.fill(0.0);
        let mut prev = 0.0f32;
        for (i, (&s, &w)) in samples.iter().zip(&self.window).enumerate() {
            self.input[i] = (s - PREEMPHASIS * prev) * w;
            prev = s;
        }
        self.plan
            .process_with_scratch(&mut self.input, &mut self.spectrum, &mut self.scratch)
            .ok()?;
        let mut log_mel = [0.0f32; MEL];
        for (cell, band) in log_mel.iter_mut().zip(&self.bank) {
            let sum: f32 = band
                .iter()
                .map(|&(bin, w)| w * self.spectrum[bin].norm_sqr())
                .sum();
            *cell = sum.max(FLOOR).ln();
        }
        let mut ceps = [0.0f32; CEPS];
        for (c, row) in ceps.iter_mut().zip(&self.dct) {
            *c = row.iter().zip(&log_mel).map(|(a, b)| a * b).sum::<f32>() * DCT_SCALE;
        }
        Some(Frame {
            ceps,
            energy_db: 10.0 * power.max(FLOOR).log10(),
        })
    }
}

#[must_use]
pub fn features(frames: &[Ceps]) -> Vec<Feat> {
    let n = frames.len();
    if n == 0 {
        return Vec::new();
    }
    let mut mean = [0.0f32; CEPS];
    for f in frames {
        for (m, v) in mean.iter_mut().zip(f) {
            *m += v;
        }
    }
    for m in &mut mean {
        *m /= n as f32;
    }
    let norm: Vec<Ceps> = frames
        .iter()
        .map(|f| {
            let mut out = [0.0f32; CEPS];
            for ((o, v), m) in out.iter_mut().zip(f).zip(&mean) {
                *o = v - m;
            }
            out
        })
        .collect();
    (0..n)
        .map(|t| {
            let ahead = &norm[(t + 2).min(n - 1)];
            let behind = &norm[t.saturating_sub(2)];
            let mut feat = [0.0f32; DIM];
            for k in 0..CEPS {
                feat[k] = norm[t][k];
                feat[CEPS + k] = DELTA_WEIGHT * (ahead[k] - behind[k]) * 0.5;
            }
            feat
        })
        .collect()
}

#[must_use]
pub fn to_float(pcm: &[i16]) -> Vec<f32> {
    pcm.iter().map(|&s| f32::from(s) / 32768.0).collect()
}

#[must_use]
pub fn frames_of(samples: &[f32]) -> Vec<Frame> {
    let mut front = Frontend::new();
    let mut out = Vec::new();
    let mut start = 0usize;
    while start + WIN <= samples.len() {
        if let Some(frame) = samples.get(start..start + WIN).and_then(|s| front.frame(s)) {
            out.push(frame);
        }
        start += HOP;
    }
    out
}
