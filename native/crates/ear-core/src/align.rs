use std::fmt;
use std::sync::Arc;

use realfft::num_complex::Complex32;
use realfft::{ComplexToReal, RealFftPlanner, RealToComplex};

pub const ALIGN_WINDOW: usize = 4096;
pub const MAX_LAG: usize = 1600;
const FFT_SIZE: usize = ALIGN_WINDOW * 2;
const PHAT_FLOOR: f32 = 1e-9;
const ENERGY_FLOOR: f64 = 1e-12;

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Alignment {
    pub lag: isize,
    pub coherence: f32,
}

pub struct Aligner {
    forward: Arc<dyn RealToComplex<f32>>,
    inverse: Arc<dyn ComplexToReal<f32>>,
    buf: Vec<f32>,
    spec_ref: Vec<Complex32>,
    spec_ch: Vec<Complex32>,
    corr: Vec<f32>,
}

impl fmt::Debug for Aligner {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Aligner")
            .field("window", &ALIGN_WINDOW)
            .finish_non_exhaustive()
    }
}

impl Default for Aligner {
    fn default() -> Self {
        Self::new()
    }
}

impl Aligner {
    #[must_use]
    pub fn new() -> Self {
        let mut planner = RealFftPlanner::<f32>::new();
        let forward = planner.plan_fft_forward(FFT_SIZE);
        let inverse = planner.plan_fft_inverse(FFT_SIZE);
        let spec_ref = forward.make_output_vec();
        let spec_ch = forward.make_output_vec();
        Self {
            forward,
            inverse,
            buf: vec![0.0; FFT_SIZE],
            spec_ref,
            spec_ch,
            corr: vec![0.0; FFT_SIZE],
        }
    }

    fn spectrum(&mut self, signal: &[f32], into_ref: bool) -> bool {
        self.buf.iter_mut().for_each(|v| *v = 0.0);
        self.buf
            .iter_mut()
            .zip(signal.iter())
            .for_each(|(slot, v)| *slot = *v);
        let out = if into_ref {
            &mut self.spec_ref
        } else {
            &mut self.spec_ch
        };
        self.forward.process(&mut self.buf, out).is_ok()
    }

    pub fn estimate(&mut self, reference: &[f32], channel: &[f32]) -> Option<Alignment> {
        if reference.len() != ALIGN_WINDOW || channel.len() != ALIGN_WINDOW {
            return None;
        }
        if !self.spectrum(reference, true) || !self.spectrum(channel, false) {
            return None;
        }
        for (c, r) in self.spec_ch.iter_mut().zip(self.spec_ref.iter()) {
            let re = c.re.mul_add(r.re, c.im * r.im);
            let im = c.im.mul_add(r.re, -(c.re * r.im));
            let mag = re.hypot(im).max(PHAT_FLOOR);
            *c = Complex32::new(re / mag, im / mag);
        }
        if let Some(first) = self.spec_ch.first_mut() {
            first.im = 0.0;
        }
        if let Some(last) = self.spec_ch.last_mut() {
            last.im = 0.0;
        }
        self.inverse
            .process(&mut self.spec_ch, &mut self.corr)
            .ok()?;
        let lag = self.peak_lag()?;
        let coherence = correlation(reference, channel, lag);
        Some(Alignment { lag, coherence })
    }

    fn peak_lag(&self) -> Option<isize> {
        let positive = self
            .corr
            .iter()
            .take(MAX_LAG.saturating_add(1))
            .enumerate()
            .map(|(i, v)| (isize::try_from(i).unwrap_or(0), *v));
        let negative = self
            .corr
            .iter()
            .rev()
            .take(MAX_LAG)
            .enumerate()
            .map(|(i, v)| {
                let back = isize::try_from(i.saturating_add(1)).unwrap_or(0);
                (back.saturating_neg(), *v)
            });
        positive
            .chain(negative)
            .max_by(|a, b| a.1.total_cmp(&b.1))
            .map(|(lag, _)| lag)
    }
}

#[must_use]
pub fn correlation(reference: &[f32], channel: &[f32], lag: isize) -> f32 {
    let shift = lag.unsigned_abs();
    let (a, b): (&[f32], &[f32]) = if lag >= 0 {
        (
            reference
                .get(..reference.len().saturating_sub(shift))
                .unwrap_or(&[]),
            channel.get(shift..).unwrap_or(&[]),
        )
    } else {
        (
            reference.get(shift..).unwrap_or(&[]),
            channel
                .get(..channel.len().saturating_sub(shift))
                .unwrap_or(&[]),
        )
    };
    let (mut dot, mut ea, mut eb) = (0.0_f64, 0.0_f64, 0.0_f64);
    for (x, y) in a.iter().zip(b.iter()) {
        let (x, y) = (f64::from(*x), f64::from(*y));
        dot += x * y;
        ea += x * x;
        eb += y * y;
    }
    if ea <= ENERGY_FLOOR || eb <= ENERGY_FLOOR {
        return 0.0;
    }
    #[allow(clippy::cast_possible_truncation)]
    let value = (dot / (ea * eb).sqrt()) as f32;
    value.clamp(-1.0, 1.0)
}
