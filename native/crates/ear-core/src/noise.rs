use crate::stft::{BINS, N_FFT, Spectrum, Stft};

const ALPHA_S: f32 = 0.8;
const ALPHA_P: f32 = 0.2;
const ALPHA_D: f32 = 0.95;
const DELTA: f32 = 2.5;
const WINDOW_FRAMES: usize = 62;
const TRACK_ALPHA: f32 = 0.95;
const TINY: f32 = 1e-12;

fn smooth_frequency(power: &[f32], out: &mut [f32]) {
    let len = power.len();
    for (k, slot) in out.iter_mut().enumerate() {
        let centre = power.get(k).copied().unwrap_or(0.0);
        let left = k
            .checked_sub(1)
            .and_then(|i| power.get(i))
            .copied()
            .unwrap_or(centre);
        let right = if k.saturating_add(1) < len {
            power.get(k.saturating_add(1)).copied().unwrap_or(centre)
        } else {
            centre
        };
        *slot = 0.25 * left + 0.5 * centre + 0.25 * right;
    }
}

#[derive(Debug, Clone)]
pub struct Mcra {
    smoothed: Vec<f32>,
    minimum: Vec<f32>,
    running: Vec<f32>,
    presence: Vec<f32>,
    noise: Vec<f32>,
    scratch: Vec<f32>,
    frames: usize,
    ready: bool,
}

impl Default for Mcra {
    fn default() -> Self {
        Self::new()
    }
}

impl Mcra {
    #[must_use]
    pub fn new() -> Self {
        Self {
            smoothed: vec![0.0; BINS],
            minimum: vec![0.0; BINS],
            running: vec![0.0; BINS],
            presence: vec![0.0; BINS],
            noise: vec![0.0; BINS],
            scratch: vec![0.0; BINS],
            frames: 0,
            ready: false,
        }
    }

    pub fn seed(&mut self, psd: &[f32]) -> bool {
        if psd.len() != BINS || psd.iter().any(|v| !v.is_finite() || *v < 0.0) {
            return false;
        }
        self.noise = psd.iter().map(|v| v.max(TINY)).collect();
        self.smoothed.clone_from(&self.noise);
        self.minimum.clone_from(&self.noise);
        self.running.clone_from(&self.noise);
        self.frames = 0;
        self.presence.iter_mut().for_each(|p| *p = 0.0);
        self.ready = true;
        true
    }

    #[must_use]
    pub fn noise(&self) -> &[f32] {
        &self.noise
    }

    #[must_use]
    pub fn presence(&self) -> &[f32] {
        &self.presence
    }

    #[must_use]
    pub fn ready(&self) -> bool {
        self.ready
    }

    pub fn update(&mut self, power: &[f32]) {
        if power.len() != BINS {
            return;
        }
        if !self.ready {
            let _ = self.seed(power);
            return;
        }
        smooth_frequency(power, &mut self.scratch);
        for (s, f) in self.smoothed.iter_mut().zip(&self.scratch) {
            *s = ALPHA_S * *s + (1.0 - ALPHA_S) * f;
        }
        self.frames = self.frames.saturating_add(1);
        let reset = self.frames >= WINDOW_FRAMES;
        if reset {
            self.frames = 0;
        }
        for (((m, r), s), (p, (n, y))) in self
            .minimum
            .iter_mut()
            .zip(self.running.iter_mut())
            .zip(&self.smoothed)
            .zip(
                self.presence
                    .iter_mut()
                    .zip(self.noise.iter_mut().zip(power)),
            )
        {
            if reset {
                *m = r.min(*s);
                *r = *s;
            } else {
                *m = m.min(*s);
                *r = r.min(*s);
            }
            let speech = if *s > DELTA * m.max(TINY) { 1.0 } else { 0.0 };
            *p = ALPHA_P * *p + (1.0 - ALPHA_P) * speech;
            let alpha = ALPHA_D + (1.0 - ALPHA_D) * *p;
            *n = (alpha * *n + (1.0 - alpha) * y).max(TINY);
        }
    }
}

#[derive(Debug, Default)]
pub struct NoiseTracker {
    stft: Stft,
    pending: Vec<f32>,
    spectrum: Option<Spectrum>,
    psd: Option<Vec<f32>>,
}

impl NoiseTracker {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    pub fn learn(&mut self, samples: &[f32]) {
        self.pending
            .extend(samples.iter().map(|v| if v.is_finite() { *v } else { 0.0 }));
        let mut spectrum = self.spectrum.take().unwrap_or_else(Stft::empty_spectrum);
        while self.pending.len() >= N_FFT {
            let frame: Vec<f32> = self.pending.drain(..N_FFT).collect();
            if !self.stft.analyze(&frame, &mut spectrum) {
                break;
            }
            let power: Vec<f32> = spectrum
                .iter()
                .map(realfft::num_complex::Complex::norm_sqr)
                .collect();
            match self.psd.as_mut() {
                Some(psd) => {
                    for (slot, p) in psd.iter_mut().zip(&power) {
                        *slot = TRACK_ALPHA * *slot + (1.0 - TRACK_ALPHA) * p;
                    }
                }
                None => self.psd = Some(power),
            }
        }
        self.spectrum = Some(spectrum);
    }

    #[must_use]
    pub fn psd(&self) -> Option<&[f32]> {
        self.psd.as_deref()
    }
}
