use std::fmt;

use crate::align::{ALIGN_WINDOW, Aligner};

pub const TAPS: usize = 512;
pub const MAX_DELAY: usize = 1600;
pub const MAX_BLOCK: usize = 16_000;
const KEEP: usize = TAPS + MAX_DELAY;
const MU: f32 = 0.35;
const MU_TRACK: f32 = 0.12;
const LEAK: f32 = 1.0e-6;
const EPS: f32 = 1.0e-6;
const FAR_ACTIVE: f32 = 1.0e-7;
const COHERENCE_MIN: f32 = 0.15;
const CONVERGED_DB: f32 = 8.0;
const REPROBE_BLOCKS: u32 = 400;
const PRE_ECHO: usize = TAPS / 4;
const SMOOTH: f32 = 0.9;
const TAPS_F: f32 = 512.0;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AecError {
    Length,
    Block,
}

impl fmt::Display for AecError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Length => f.write_str("ear.aec.length"),
            Self::Block => f.write_str("ear.aec.block"),
        }
    }
}

impl std::error::Error for AecError {}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct AecStats {
    pub erle_db: f32,
    pub delay: usize,
    pub converged: bool,
    pub double_talk: bool,
    pub far_active: bool,
}

pub struct EchoCanceller {
    weights: Vec<f32>,
    hist: Vec<f32>,
    delay: usize,
    probe_far: Vec<f32>,
    probe_near: Vec<f32>,
    aligner: Aligner,
    erle_db: f32,
    converged: bool,
    stalled: u32,
    stats: AecStats,
}

impl fmt::Debug for EchoCanceller {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("EchoCanceller")
            .field("delay", &self.delay)
            .field("erle_db", &self.erle_db)
            .field("converged", &self.converged)
            .finish_non_exhaustive()
    }
}

impl Default for EchoCanceller {
    fn default() -> Self {
        Self::new()
    }
}

fn energy(v: &[f32]) -> f32 {
    let n = v.len().max(1);
    #[allow(clippy::cast_precision_loss)]
    let count = n as f32;
    v.iter().map(|x| x * x).sum::<f32>() / count
}

fn clean(v: f32) -> f32 {
    if v.is_finite() {
        v.clamp(-1.0, 1.0)
    } else {
        0.0
    }
}

impl EchoCanceller {
    #[must_use]
    pub fn new() -> Self {
        Self {
            weights: vec![0.0; TAPS],
            hist: vec![0.0; KEEP],
            delay: 0,
            probe_far: Vec::with_capacity(ALIGN_WINDOW),
            probe_near: Vec::with_capacity(ALIGN_WINDOW),
            aligner: Aligner::new(),
            erle_db: 0.0,
            converged: false,
            stalled: 0,
            stats: AecStats {
                erle_db: 0.0,
                delay: 0,
                converged: false,
                double_talk: false,
                far_active: false,
            },
        }
    }

    #[must_use]
    pub fn stats(&self) -> AecStats {
        self.stats
    }

    pub fn reset(&mut self) {
        *self = Self::new();
    }

    fn probe(&mut self, near: &[f32], far: &[f32]) {
        let room = ALIGN_WINDOW.saturating_sub(self.probe_far.len());
        self.probe_far.extend(far.iter().take(room));
        self.probe_near.extend(near.iter().take(room));
        if self.probe_far.len() < ALIGN_WINDOW {
            return;
        }
        if let Some(found) = self.aligner.estimate(&self.probe_far, &self.probe_near) {
            if found.coherence >= COHERENCE_MIN && found.lag >= 0 {
                let lag = usize::try_from(found.lag).unwrap_or(0).min(MAX_DELAY);
                self.delay = lag.saturating_sub(PRE_ECHO);
            }
        }
        self.probe_far.clear();
        self.probe_near.clear();
    }

    pub fn process(&mut self, near: &[f32], far: &[f32]) -> Result<Vec<f32>, AecError> {
        if near.len() != far.len() {
            return Err(AecError::Length);
        }
        if near.len() > MAX_BLOCK {
            return Err(AecError::Block);
        }
        let near: Vec<f32> = near.iter().map(|v| clean(*v)).collect();
        let far: Vec<f32> = far.iter().map(|v| clean(*v)).collect();
        let far_e = energy(&far);
        let far_active = far_e > FAR_ACTIVE;
        let near_e = energy(&near);
        if far_active && (!self.converged || self.stalled >= REPROBE_BLOCKS) {
            self.probe(&near, &far);
        }
        let count = near.len();
        self.hist.extend_from_slice(&far);
        let base = self.hist.len().saturating_sub(count);
        let adapt_gate = far_active;
        let mu = if self.converged { MU_TRACK } else { MU };
        let mut out = Vec::with_capacity(count);
        let mut err_e = 0.0_f32;
        let mut frozen = false;
        for (j, d) in near.iter().enumerate() {
            let end = base
                .saturating_add(j)
                .saturating_add(1)
                .saturating_sub(self.delay);
            let start = end.saturating_sub(TAPS);
            let Some(win) = self.hist.get(start..end) else {
                out.push(*d);
                continue;
            };
            let (mut y, mut px) = (0.0_f32, 0.0_f32);
            for (w, x) in self.weights.iter().zip(win.iter()) {
                y = w.mul_add(*x, y);
                px = x.mul_add(*x, px);
            }
            let e = clean(*d - y);
            err_e = e.mul_add(e, err_e);
            let talking = self.converged && e.abs() > 1.5 * y.abs() + 0.01;
            if talking {
                frozen = true;
            }
            if adapt_gate && !talking {
                let g = mu * e / (px + EPS * TAPS_F);
                for (w, x) in self.weights.iter_mut().zip(win.iter()) {
                    *w = g.mul_add(*x, *w * (1.0 - LEAK));
                }
            }
            out.push(e);
        }
        let drop = self.hist.len().saturating_sub(KEEP);
        self.hist.drain(..drop);
        #[allow(clippy::cast_precision_loss)]
        let n = count.max(1) as f32;
        let err_e = err_e / n;
        if far_active && !frozen && near_e > EPS {
            let ratio = near_e / err_e.max(EPS * 1.0e-3);
            let db = 10.0 * ratio.max(1.0e-6).log10();
            self.erle_db = SMOOTH.mul_add(self.erle_db, (1.0 - SMOOTH) * db);
            self.converged = self.erle_db >= CONVERGED_DB;
            self.stalled = if self.erle_db < CONVERGED_DB {
                self.stalled.saturating_add(1)
            } else {
                0
            };
        }
        self.stats = AecStats {
            erle_db: self.erle_db,
            delay: self.delay,
            converged: self.converged,
            double_talk: frozen,
            far_active,
        };
        Ok(out)
    }
}
