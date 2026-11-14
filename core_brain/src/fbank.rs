use std::f32::consts::PI;
use std::sync::Arc;

use realfft::{RealFftPlanner, RealToComplex};

use crate::error::{BrainError, BrainResult};

pub const SAMPLE_RATE: usize = 16_000;
pub const MELS: usize = 80;
const FRAME: usize = 400;
const SHIFT: usize = 160;
const FFT: usize = 512;
const LOW_HZ: f32 = 20.0;
const HIGH_HZ: f32 = 8_000.0;
const PREEMPH: f32 = 0.97;
const FLOOR: f32 = 1.192_092_9e-7;
const PCM_SCALE: f32 = 32_768.0;
pub const MIN_SAMPLES: usize = SAMPLE_RATE / 2;
pub const MAX_SAMPLES: usize = SAMPLE_RATE * 60;

fn mel(hz: f32) -> f32 {
    1127.0 * (1.0 + hz / 700.0).ln()
}

pub struct Fbank {
    fft: Arc<dyn RealToComplex<f32>>,
    window: Vec<f32>,
    banks: Vec<Vec<f32>>,
}

impl std::fmt::Debug for Fbank {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("Fbank(..)")
    }
}

impl Default for Fbank {
    fn default() -> Self {
        Self::new()
    }
}

#[allow(clippy::cast_precision_loss)]
impl Fbank {
    #[must_use]
    pub fn new() -> Self {
        let fft = RealFftPlanner::<f32>::new().plan_fft_forward(FFT);
        let window = (0..FRAME)
            .map(|n| {
                let phase = 2.0 * PI * n as f32 / (FRAME - 1) as f32;
                (0.5 - 0.5 * phase.cos()).powf(0.85)
            })
            .collect();
        let (lo, hi) = (mel(LOW_HZ), mel(HIGH_HZ));
        let step = (hi - lo) / (MELS + 1) as f32;
        let bins = FFT / 2;
        let hz_per_bin = SAMPLE_RATE as f32 / FFT as f32;
        let banks = (0..MELS)
            .map(|m| {
                let base = m as f32;
                let (a, b, c) = (
                    step.mul_add(base, lo),
                    step.mul_add(base + 1.0, lo),
                    step.mul_add(base + 2.0, lo),
                );
                (0..bins)
                    .map(|k| {
                        let x = mel(hz_per_bin * k as f32);
                        if x > a && x < b {
                            (x - a) / (b - a)
                        } else if x >= b && x < c {
                            (c - x) / (c - b)
                        } else {
                            0.0
                        }
                    })
                    .collect()
            })
            .collect();
        Self { fft, window, banks }
    }

    pub fn compute(&self, pcm: &[f32]) -> BrainResult<Vec<f32>> {
        if pcm.len() < MIN_SAMPLES {
            return Err(BrainError::Embedding("too_short"));
        }
        if pcm.len() > MAX_SAMPLES {
            return Err(BrainError::Embedding("too_long"));
        }
        if pcm.iter().any(|v| !v.is_finite()) {
            return Err(BrainError::Embedding("non_finite"));
        }
        let mut out: Vec<f32> = Vec::new();
        let mut input = self.fft.make_input_vec();
        let mut spectrum = self.fft.make_output_vec();
        let mut scratch = self.fft.make_scratch_vec();
        for window in pcm.windows(FRAME).step_by(SHIFT) {
            let scaled: Vec<f32> = window.iter().map(|v| v * PCM_SCALE).collect();
            let mean = scaled.iter().sum::<f32>() / FRAME as f32;
            let centred: Vec<f32> = scaled.iter().map(|v| v - mean).collect();
            input.fill(0.0);
            let head = centred.first().copied().unwrap_or(0.0);
            let previous = std::iter::once(head).chain(centred.iter().copied());
            for ((dst, cur), (prev, w)) in input
                .iter_mut()
                .zip(centred.iter().copied())
                .zip(previous.zip(self.window.iter().copied()))
            {
                *dst = PREEMPH.mul_add(-prev, cur) * w;
            }
            self.fft
                .process_with_scratch(&mut input, &mut spectrum, &mut scratch)
                .map_err(|_| BrainError::Embedding("fft"))?;
            let power: Vec<f32> = spectrum
                .iter()
                .take(FFT / 2)
                .map(realfft::num_complex::Complex::norm_sqr)
                .collect();
            for bank in &self.banks {
                let energy: f32 = bank.iter().zip(&power).map(|(w, p)| w * p).sum();
                out.push(energy.max(FLOOR).ln());
            }
        }
        let frames = out.len() / MELS;
        let mut means = vec![0.0_f32; MELS];
        for row in out.chunks_exact(MELS) {
            for (acc, v) in means.iter_mut().zip(row) {
                *acc += v;
            }
        }
        let count = frames.max(1) as f32;
        for row in out.chunks_exact_mut(MELS) {
            for (v, acc) in row.iter_mut().zip(&means) {
                *v -= acc / count;
            }
        }
        Ok(out)
    }
}
