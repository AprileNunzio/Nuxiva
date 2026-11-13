use std::collections::BTreeSet;

use crate::gate_seeds::SEEDS;

pub const DIM: usize = 1024;
pub const MAX_GATE_TEXT: usize = 4_000;
const TOP_K: usize = 3;
const SHARPNESS: f32 = 14.0;
const MIN_DROP_CONFIDENCE: f32 = 0.5;
const REPEAT_SONG: f32 = 0.45;
const REPEAT_MIN_WORDS: usize = 8;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Intent {
    Command,
    Question,
    Song,
    Chatter,
    Noise,
}

impl Intent {
    pub const ALL: [Self; 5] = [
        Self::Command,
        Self::Question,
        Self::Song,
        Self::Chatter,
        Self::Noise,
    ];

    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Command => "command",
            Self::Question => "question",
            Self::Song => "song",
            Self::Chatter => "chatter",
            Self::Noise => "noise",
        }
    }

    #[must_use]
    pub const fn actionable(self) -> bool {
        matches!(self, Self::Command | Self::Question)
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct GateVerdict {
    pub intent: Intent,
    pub confidence: f32,
    pub drop: bool,
    pub reason: &'static str,
}

#[derive(Debug, Clone)]
pub struct IntentGate {
    prototypes: Vec<(Intent, Vec<f32>)>,
}

impl Default for IntentGate {
    fn default() -> Self {
        Self::new()
    }
}

fn fnv(bytes: &[u8]) -> u64 {
    bytes.iter().fold(0xcbf2_9ce4_8422_2325, |h, b| {
        (h ^ u64::from(*b)).wrapping_mul(0x0100_0000_01b3)
    })
}

fn tokens(text: &str) -> Vec<String> {
    text.chars()
        .map(|c| {
            if c.is_alphanumeric() || c == '\'' {
                c.to_lowercase().next().unwrap_or(c)
            } else {
                ' '
            }
        })
        .collect::<String>()
        .split_whitespace()
        .map(str::to_owned)
        .collect()
}

fn add(vec: &mut [f32], key: &[u8], weight: f32) {
    let h = fnv(key);
    let slot = usize::try_from(h.checked_rem(DIM as u64).unwrap_or(0)).unwrap_or(0);
    let sign = if (h >> 63) == 0 { 1.0 } else { -1.0 };
    if let Some(cell) = vec.get_mut(slot) {
        *cell += sign * weight;
    }
}

#[must_use]
pub fn embed(text: &str) -> Vec<f32> {
    let words = tokens(text);
    let mut vec = vec![0.0_f32; DIM];
    for word in &words {
        add(&mut vec, format!("w:{word}").as_bytes(), 1.0);
        let padded: Vec<char> = format!(" {word} ").chars().collect();
        for n in 3..=4 {
            for gram in padded.windows(n) {
                let key: String = gram.iter().collect();
                add(&mut vec, format!("g:{key}").as_bytes(), 0.5);
            }
        }
    }
    for pair in words.windows(2) {
        add(&mut vec, format!("b:{}", pair.join(" ")).as_bytes(), 0.7);
    }
    for v in &mut vec {
        *v = v.signum() * v.abs().sqrt();
    }
    let norm = vec.iter().map(|v| v * v).sum::<f32>().sqrt();
    if norm > 1e-9 {
        for v in &mut vec {
            *v /= norm;
        }
    }
    vec
}

fn dot(a: &[f32], b: &[f32]) -> f32 {
    a.iter().zip(b.iter()).map(|(x, y)| x * y).sum()
}

fn repetition(words: &[String]) -> f32 {
    if words.len() < REPEAT_MIN_WORDS {
        return 0.0;
    }
    let unique: BTreeSet<&String> = words.iter().collect();
    #[allow(clippy::cast_precision_loss)]
    let ratio = unique.len() as f32 / words.len() as f32;
    1.0 - ratio
}

impl IntentGate {
    #[must_use]
    pub fn new() -> Self {
        Self {
            prototypes: SEEDS.iter().map(|(i, t)| (*i, embed(t))).collect(),
        }
    }

    fn scores(&self, probe: &[f32]) -> Vec<(Intent, f32)> {
        Intent::ALL
            .iter()
            .map(|intent| {
                let mut sims: Vec<f32> = self
                    .prototypes
                    .iter()
                    .filter(|(i, _)| i == intent)
                    .map(|(_, p)| dot(p, probe))
                    .collect();
                sims.sort_by(|a, b| b.total_cmp(a));
                let top: Vec<f32> = sims.into_iter().take(TOP_K).collect();
                #[allow(clippy::cast_precision_loss)]
                let mean = top.iter().sum::<f32>() / top.len().max(1) as f32;
                (*intent, mean)
            })
            .collect()
    }

    #[must_use]
    pub fn judge(&self, text: &str, named: bool) -> GateVerdict {
        let text: String = text.chars().take(MAX_GATE_TEXT).collect();
        let words = tokens(&text);
        if words.is_empty() {
            return GateVerdict {
                intent: Intent::Noise,
                confidence: 1.0,
                drop: true,
                reason: "vuoto",
            };
        }
        let mut scores = self.scores(&embed(&text));
        if repetition(&words) >= REPEAT_SONG {
            scores
                .iter_mut()
                .filter(|(i, _)| *i == Intent::Song)
                .for_each(|(_, s)| *s += 0.25);
        }
        let exp: Vec<f32> = scores.iter().map(|(_, s)| (s * SHARPNESS).exp()).collect();
        let total: f32 = exp.iter().sum::<f32>().max(1e-9);
        let best = scores
            .iter()
            .zip(exp.iter())
            .max_by(|a, b| a.0.1.total_cmp(&b.0.1))
            .map_or((Intent::Noise, 0.0), |((i, _), e)| (*i, e / total));
        let (intent, confidence) = best;
        if named {
            return GateVerdict {
                intent,
                confidence,
                drop: false,
                reason: "chiamato per nome",
            };
        }
        let drop = !intent.actionable() && confidence >= MIN_DROP_CONFIDENCE;
        GateVerdict {
            intent,
            confidence,
            drop,
            reason: if drop {
                "senza intento di comando"
            } else {
                "ok"
            },
        }
    }
}
