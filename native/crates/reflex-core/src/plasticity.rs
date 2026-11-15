#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};
use std::sync::RwLock;

pub const EMBED_DIM: usize = 1024;
pub const CONFORMAL_THRESHOLD: f32 = 0.82;
pub const MAX_PROTOTYPES: usize = 2048;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Prototype {
    pub query_exemplar: String,
    pub intent: String,
    pub action: String,
    pub embedding: Vec<f32>,
    pub reinforcement_count: u32,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PredictionResult {
    pub intent: String,
    pub action: String,
    pub confidence: f32,
    pub is_guaranteed: bool,
    pub conformal_margin: f32,
}

#[derive(Debug)]
pub struct PlasticityMemory {
    prototypes: RwLock<Vec<Prototype>>,
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

fn add_feature(vec: &mut [f32], key: &[u8], weight: f32) {
    let h = fnv(key);
    let rem = h.checked_rem(EMBED_DIM as u64).unwrap_or(0);
    let slot = usize::try_from(rem).unwrap_or(0);
    let sign = if (h >> 63) == 0 { 1.0 } else { -1.0 };
    if let Some(cell) = vec.get_mut(slot) {
        *cell += sign * weight;
    }
}

#[must_use]
pub fn compute_embedding(text: &str) -> Vec<f32> {
    let words = tokens(text);
    let mut vec = vec![0.0_f32; EMBED_DIM];
    for word in &words {
        add_feature(&mut vec, format!("w:{word}").as_bytes(), 1.0);
        let padded: Vec<char> = format!(" {word} ").chars().collect();
        for n in 3..=4 {
            for gram in padded.windows(n) {
                let key: String = gram.iter().collect();
                add_feature(&mut vec, format!("g:{key}").as_bytes(), 0.5);
            }
        }
    }
    for pair in words.windows(2) {
        add_feature(&mut vec, format!("b:{}", pair.join(" ")).as_bytes(), 0.7);
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

fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    a.iter().zip(b.iter()).map(|(x, y)| x * y).sum()
}

impl Default for PlasticityMemory {
    fn default() -> Self {
        Self::new()
    }
}

impl PlasticityMemory {
    #[must_use]
    pub fn new() -> Self {
        let initial = vec![
            Prototype {
                query_exemplar: "accendi la luce".to_owned(),
                intent: "action_direct".to_owned(),
                action: "home_assistant.toggle_light".to_owned(),
                embedding: compute_embedding("accendi la luce"),
                reinforcement_count: 5,
            },
            Prototype {
                query_exemplar: "turn on the light".to_owned(),
                intent: "action_direct".to_owned(),
                action: "home_assistant.toggle_light".to_owned(),
                embedding: compute_embedding("turn on the light"),
                reinforcement_count: 5,
            },
            Prototype {
                query_exemplar: "spegni le luci".to_owned(),
                intent: "action_direct".to_owned(),
                action: "home_assistant.toggle_light".to_owned(),
                embedding: compute_embedding("spegni le luci"),
                reinforcement_count: 5,
            },
            Prototype {
                query_exemplar: "stop the music".to_owned(),
                intent: "action_direct".to_owned(),
                action: "media_player.stop".to_owned(),
                embedding: compute_embedding("stop the music"),
                reinforcement_count: 5,
            },
            Prototype {
                query_exemplar: "metti in pausa la musica".to_owned(),
                intent: "action_direct".to_owned(),
                action: "media_player.pause".to_owned(),
                embedding: compute_embedding("metti in pausa la musica"),
                reinforcement_count: 5,
            },
            Prototype {
                query_exemplar: "spiega la teoria della relatività e l'effetto fotoelettrico"
                    .to_owned(),
                intent: "complex_task".to_owned(),
                action: "system2_latent_engine".to_owned(),
                embedding: compute_embedding(
                    "spiega la teoria della relatività e l'effetto fotoelettrico",
                ),
                reinforcement_count: 3,
            },
            Prototype {
                query_exemplar: "cerca sul web gli ultimi aggiornamenti di oggi".to_owned(),
                intent: "browser_action".to_owned(),
                action: "browser.search".to_owned(),
                embedding: compute_embedding("cerca sul web gli ultimi aggiornamenti di oggi"),
                reinforcement_count: 3,
            },
        ];

        Self {
            prototypes: RwLock::new(initial),
        }
    }

    #[must_use]
    pub fn predict(&self, query: &str) -> Option<PredictionResult> {
        let query_emb = compute_embedding(query);
        let guard = self.prototypes.read().ok()?;
        if guard.is_empty() {
            return None;
        }

        let mut scored: Vec<(f32, &Prototype)> = guard
            .iter()
            .map(|p| (cosine_similarity(&query_emb, &p.embedding), p))
            .collect();

        scored.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal));

        let (best_sim, best_proto) = scored.first()?;
        let second_sim = scored.get(1).map_or(0.0_f32, |(s, _)| *s);
        let margin = best_sim - second_sim;

        let is_guaranteed = *best_sim >= CONFORMAL_THRESHOLD && margin >= 0.05;

        Some(PredictionResult {
            intent: best_proto.intent.clone(),
            action: best_proto.action.clone(),
            confidence: best_sim.clamp(0.0, 1.0),
            is_guaranteed,
            conformal_margin: margin,
        })
    }

    #[must_use]
    pub fn reinforce(&self, query: &str, intent: &str, action: &str) -> bool {
        let query_emb = compute_embedding(query);
        let Ok(mut guard) = self.prototypes.write() else {
            return false;
        };

        for p in guard.iter_mut() {
            if p.intent == intent && p.action == action {
                let sim = cosine_similarity(&query_emb, &p.embedding);
                if sim > 0.85 {
                    p.reinforcement_count = p.reinforcement_count.saturating_add(1);
                    for (dst, src) in p.embedding.iter_mut().zip(query_emb.iter()) {
                        *dst = 0.9 * (*dst) + 0.1 * (*src);
                    }
                    let norm = p.embedding.iter().map(|v| v * v).sum::<f32>().sqrt();
                    if norm > 1e-9 {
                        for v in &mut p.embedding {
                            *v /= norm;
                        }
                    }
                    return true;
                }
            }
        }

        if guard.len() >= MAX_PROTOTYPES {
            guard.remove(0);
        }

        guard.push(Prototype {
            query_exemplar: query.to_owned(),
            intent: intent.to_owned(),
            action: action.to_owned(),
            embedding: query_emb,
            reinforcement_count: 1,
        });

        true
    }
}
