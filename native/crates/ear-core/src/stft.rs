use std::f32::consts::PI;
use std::fmt;
use std::sync::Arc;

use realfft::num_complex::Complex32;
use realfft::{ComplexToReal, RealFftPlanner, RealToComplex};

pub const RATE: f32 = 16_000.0;
pub const N_FFT: usize = 512;
pub const HOP: usize = N_FFT / 2;
pub const BINS: usize = N_FFT / 2 + 1;

pub type Spectrum = Vec<Complex32>;

pub struct Stft {
    forward: Arc<dyn RealToComplex<f32>>,
    inverse: Arc<dyn ComplexToReal<f32>>,
    window: Vec<f32>,
    frame: Vec<f32>,
    synth: Vec<f32>,
}

impl fmt::Debug for Stft {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Stft").field("n_fft", &N_FFT).finish()
    }
}

impl Default for Stft {
    fn default() -> Self {
        Self::new()
    }
}

#[allow(clippy::cast_precision_loss)]
fn sqrt_hann() -> Vec<f32> {
    (0..N_FFT)
        .map(|i| {
            let phase = 2.0 * PI * i as f32 / N_FFT as f32;
            (0.5 - 0.5 * phase.cos()).max(0.0).sqrt()
        })
        .collect()
}

#[allow(clippy::cast_precision_loss)]
#[must_use]
pub fn bin_hz(bin: usize) -> f32 {
    bin as f32 * RATE / N_FFT as f32
}

impl Stft {
    #[must_use]
    pub fn new() -> Self {
        let mut planner = RealFftPlanner::<f32>::new();
        Self {
            forward: planner.plan_fft_forward(N_FFT),
            inverse: planner.plan_fft_inverse(N_FFT),
            window: sqrt_hann(),
            frame: vec![0.0; N_FFT],
            synth: vec![0.0; N_FFT],
        }
    }

    #[must_use]
    pub fn empty_spectrum() -> Spectrum {
        vec![Complex32::new(0.0, 0.0); BINS]
    }

    pub fn analyze(&mut self, samples: &[f32], out: &mut Spectrum) -> bool {
        if samples.len() != N_FFT || out.len() != BINS {
            return false;
        }
        for ((slot, sample), w) in self.frame.iter_mut().zip(samples).zip(&self.window) {
            *slot = sample * w;
        }
        self.forward.process(&mut self.frame, out).is_ok()
    }

    pub fn synthesize(&mut self, spectrum: &mut Spectrum) -> Option<&[f32]> {
        if spectrum.len() != BINS {
            return None;
        }
        if let Some(first) = spectrum.first_mut() {
            first.im = 0.0;
        }
        if let Some(last) = spectrum.last_mut() {
            last.im = 0.0;
        }
        self.inverse.process(spectrum, &mut self.synth).ok()?;
        #[allow(clippy::cast_precision_loss)]
        let scale = 1.0 / N_FFT as f32;
        for (value, w) in self.synth.iter_mut().zip(&self.window) {
            *value *= scale * w;
        }
        Some(&self.synth)
    }
}
