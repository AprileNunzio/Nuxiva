use std::collections::VecDeque;

use zeroize::Zeroize;

use crate::policy::{Policy, Rejection};

pub const MAX_DIM: usize = 4096;
pub const MAX_FRAMES: usize = 4096;
const MAX_LABEL: usize = 96;
const INDICATOR_GRACE_MS: u64 = 10_000;
const DECAY_MS: f64 = 30_000.0;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Source {
    Screen,
    Webcam,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FrameMeta {
    pub source: Source,
    pub app: String,
    pub title: String,
    pub at_ms: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PushOutcome {
    Stored,
    Rejected(Rejection),
}

#[derive(Debug, Clone, PartialEq)]
pub struct Hit {
    pub app: String,
    pub source: Source,
    pub at_ms: u64,
    pub score: f32,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Indicator {
    pub active: bool,
    pub source: Option<Source>,
    pub frames: usize,
    pub last_ms: Option<u64>,
}

#[derive(Debug)]
struct Frame {
    source: Source,
    app: String,
    at_ms: u64,
    vector: Vec<f32>,
}

impl Drop for Frame {
    fn drop(&mut self) {
        self.vector.zeroize();
    }
}

#[derive(Debug)]
pub struct VisualBuffer {
    policy: Policy,
    frames: VecDeque<Frame>,
    dim: Option<usize>,
    last_push: Option<u64>,
}

fn unit(v: &[f32]) -> Option<Vec<f32>> {
    if v.is_empty() || v.len() > MAX_DIM || v.iter().any(|x| !x.is_finite()) {
        return None;
    }
    let norm = v.iter().map(|x| x * x).sum::<f32>().sqrt();
    if norm < 1e-9 {
        return None;
    }
    Some(v.iter().map(|x| x / norm).collect())
}

fn label(text: &str) -> String {
    text.chars()
        .filter(|c| !c.is_control())
        .take(MAX_LABEL)
        .collect()
}

impl VisualBuffer {
    #[must_use]
    pub fn new(policy: Policy) -> Self {
        Self {
            policy: policy.sanitized(),
            frames: VecDeque::new(),
            dim: None,
            last_push: None,
        }
    }

    pub fn set_policy(&mut self, policy: Policy) {
        let revoked = self.policy.consent && !policy.consent;
        self.policy = policy.sanitized();
        if revoked {
            self.wipe();
        }
        while self.frames.len() > self.policy.capacity {
            self.frames.pop_front();
        }
    }

    pub fn wipe(&mut self) {
        self.frames.clear();
        self.dim = None;
        self.last_push = None;
    }

    pub fn expire(&mut self, now_ms: u64) {
        let ttl = self.policy.ttl_ms;
        while self
            .frames
            .front()
            .is_some_and(|f| now_ms.saturating_sub(f.at_ms) > ttl)
        {
            self.frames.pop_front();
        }
        if self.frames.is_empty() {
            self.dim = None;
        }
    }

    pub fn push(&mut self, meta: &FrameMeta, embedding: &[f32]) -> PushOutcome {
        if !self.policy.consent {
            return PushOutcome::Rejected(Rejection::NoConsent);
        }
        if self.policy.is_sensitive(&meta.app, &meta.title) {
            return PushOutcome::Rejected(Rejection::Sensitive);
        }
        if self
            .last_push
            .is_some_and(|t| meta.at_ms.saturating_sub(t) < self.policy.interval_ms)
        {
            return PushOutcome::Rejected(Rejection::TooSoon);
        }
        let Some(vector) = unit(embedding) else {
            return PushOutcome::Rejected(Rejection::Invalid);
        };
        self.expire(meta.at_ms);
        if self.dim.is_some_and(|d| d != vector.len()) {
            return PushOutcome::Rejected(Rejection::Invalid);
        }
        self.dim = Some(vector.len());
        if self.frames.len() >= self.policy.capacity {
            self.frames.pop_front();
        }
        self.frames.push_back(Frame {
            source: meta.source,
            app: label(&meta.app),
            at_ms: meta.at_ms,
            vector,
        });
        self.last_push = Some(meta.at_ms);
        PushOutcome::Stored
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.frames.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.frames.is_empty()
    }

    #[must_use]
    pub fn query(&self, probe: &[f32], now_ms: u64, k: usize) -> Vec<Hit> {
        let Some(probe) = unit(probe) else {
            return Vec::new();
        };
        if self.dim != Some(probe.len()) {
            return Vec::new();
        }
        let mut hits: Vec<Hit> = self
            .frames
            .iter()
            .filter(|f| now_ms.saturating_sub(f.at_ms) <= self.policy.ttl_ms)
            .map(|f| Hit {
                app: f.app.clone(),
                source: f.source,
                at_ms: f.at_ms,
                score: f.vector.iter().zip(probe.iter()).map(|(a, b)| a * b).sum(),
            })
            .collect();
        hits.sort_by(|a, b| b.score.total_cmp(&a.score));
        hits.truncate(k.min(64));
        hits
    }

    #[must_use]
    pub fn context(&self, now_ms: u64) -> Option<Vec<f32>> {
        let dim = self.dim?;
        let mut acc = vec![0.0_f32; dim];
        let mut total = 0.0_f64;
        for f in self
            .frames
            .iter()
            .filter(|f| now_ms.saturating_sub(f.at_ms) <= self.policy.ttl_ms)
        {
            #[allow(clippy::cast_precision_loss)]
            let age = now_ms.saturating_sub(f.at_ms) as f64;
            let weight = (-age / DECAY_MS).exp();
            total += weight;
            #[allow(clippy::cast_possible_truncation)]
            let w = weight as f32;
            acc.iter_mut()
                .zip(f.vector.iter())
                .for_each(|(a, v)| *a += w * v);
        }
        if total <= 1e-9 {
            return None;
        }
        unit(&acc)
    }

    #[must_use]
    pub fn current_app(&self, now_ms: u64) -> Option<&str> {
        self.frames
            .back()
            .filter(|f| now_ms.saturating_sub(f.at_ms) <= self.policy.ttl_ms)
            .map(|f| f.app.as_str())
    }

    #[must_use]
    pub fn indicator(&self, now_ms: u64) -> Indicator {
        let last = self.frames.back();
        let live = self.policy.consent
            && last.is_some_and(|f| {
                now_ms.saturating_sub(f.at_ms)
                    <= INDICATOR_GRACE_MS.max(self.policy.interval_ms.saturating_mul(3))
            });
        Indicator {
            active: live,
            source: last.map(|f| f.source),
            frames: self.frames.len(),
            last_ms: last.map(|f| f.at_ms),
        }
    }
}
