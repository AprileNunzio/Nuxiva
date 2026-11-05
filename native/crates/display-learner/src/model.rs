use serde::{Deserialize, Serialize};

use crate::context::{BIAS, ContextVector, FEATURES};
use crate::policy::{LearnerPolicy, decay};

const WEIGHT_CAP: f32 = 1.0e6;

#[derive(Debug, Clone, Copy, PartialEq, Default, Serialize, Deserialize)]
pub struct Estimate {
    pub mean: f32,
    pub evidence: f32,
}

impl Estimate {
    #[must_use]
    pub fn uncertainty(&self) -> f32 {
        1.0 / (1.0 + self.evidence.max(0.0)).sqrt()
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Model {
    reward: Vec<f32>,
    weight: Vec<f32>,
    at_ms: u64,
}

impl Default for Model {
    fn default() -> Self {
        Self {
            reward: vec![0.0; FEATURES],
            weight: vec![0.0; FEATURES],
            at_ms: 0,
        }
    }
}

impl Model {
    #[must_use]
    pub fn sane(&self) -> bool {
        self.reward.len() == FEATURES
            && self.weight.len() == FEATURES
            && self
                .reward
                .iter()
                .zip(&self.weight)
                .all(|(r, w)| r.is_finite() && w.is_finite() && *w >= 0.0 && r.abs() <= *w + 1e-3)
    }

    fn factor(&self, now_ms: u64, policy: &LearnerPolicy) -> f32 {
        decay(now_ms.saturating_sub(self.at_ms), policy.half_life_ms)
    }

    pub fn observe(
        &mut self,
        ctx: &ContextVector,
        reward: f32,
        weight: f32,
        now_ms: u64,
        policy: &LearnerPolicy,
    ) {
        if !(reward.is_finite() && weight.is_finite()) || weight <= 0.0 {
            return;
        }
        let f = self.factor(now_ms, policy);
        for v in self.reward.iter_mut().chain(self.weight.iter_mut()) {
            *v *= f;
        }
        self.at_ms = self.at_ms.max(now_ms);
        let reward = reward.clamp(-1.0, 1.0);
        for i in ctx.features() {
            if let (Some(r), Some(w)) = (self.reward.get_mut(i), self.weight.get_mut(i)) {
                *w = (*w + weight).min(WEIGHT_CAP);
                *r = (*r + reward * weight).clamp(-*w, *w);
            }
        }
    }

    fn mean_at(&self, i: usize, f: f32, prior: f32) -> Option<(f32, f32)> {
        let (r, w) = (self.reward.get(i)? * f, self.weight.get(i)? * f);
        Some((r / (w + prior), w))
    }

    #[must_use]
    pub fn estimate(&self, ctx: &ContextVector, now_ms: u64, policy: &LearnerPolicy) -> Estimate {
        let f = self.factor(now_ms, policy);
        let Some((base, evidence)) = self.mean_at(BIAS, f, policy.prior) else {
            return Estimate::default();
        };
        let mut mean = base;
        for i in ctx.features().into_iter().filter(|i| *i != BIAS) {
            if let Some((m, w)) = self.mean_at(i, f, policy.prior) {
                mean += (m - base) * w / (w + policy.prior);
            }
        }
        Estimate {
            mean: mean.clamp(-1.0, 1.0),
            evidence,
        }
    }

    #[must_use]
    pub const fn at_ms(&self) -> u64 {
        self.at_ms
    }
}
