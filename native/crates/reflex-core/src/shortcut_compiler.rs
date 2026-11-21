#![forbid(unsafe_code)]

use std::collections::BTreeMap;
use std::sync::RwLock;

use serde::{Deserialize, Serialize};

use crate::plasticity::{EMBED_DIM, compute_embedding};

pub const MIN_CONSOLIDATION_COUNT: u32 = 3;
pub const CLUSTER_SIMILARITY_FLOOR: f32 = 0.55;
pub const MAX_TRACES: usize = 512;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SlowPathTrace {
    pub queries: Vec<String>,
    pub intent: String,
    pub action_target: String,
    pub deterministic_output: Option<String>,
    pub embedding: Vec<f32>,
    pub hits: u32,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CompiledShortcut {
    pub shortcut_id: String,
    pub intent: String,
    pub action_target: String,
    pub deterministic_output: Option<String>,
    pub exemplars: Vec<String>,
    pub consolidated_hits: u32,
    pub promoted_to_fast_path: bool,
}

#[derive(Debug, Default)]
pub struct ShortcutCompiler {
    traces: RwLock<Vec<SlowPathTrace>>,
    compiled: RwLock<BTreeMap<String, CompiledShortcut>>,
}

fn cosine(a: &[f32], b: &[f32]) -> f32 {
    a.iter().zip(b.iter()).map(|(x, y)| x * y).sum()
}

fn blend_and_normalize(dst: &mut [f32], src: &[f32]) {
    if dst.len() != EMBED_DIM || src.len() != EMBED_DIM {
        return;
    }
    for (d, s) in dst.iter_mut().zip(src.iter()) {
        *d = 0.85 * (*d) + 0.15 * (*s);
    }
    let norm = dst.iter().map(|v| v * v).sum::<f32>().sqrt();
    if norm > 1e-9 {
        for v in dst.iter_mut() {
            *v /= norm;
        }
    }
}

impl ShortcutCompiler {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    #[must_use]
    pub fn record_slow_resolution(
        &self,
        query: &str,
        intent: &str,
        action_target: &str,
        deterministic_output: Option<&str>,
    ) -> Option<CompiledShortcut> {
        let trimmed_q = query.trim();
        let trimmed_act = action_target.trim();
        if trimmed_q.is_empty() || trimmed_act.is_empty() {
            return None;
        }
        let emb = compute_embedding(trimmed_q);
        let mut guard = self.traces.write().ok()?;

        for trace in guard.iter_mut() {
            if trace.action_target == trimmed_act && trace.intent == intent {
                let sim = cosine(&emb, &trace.embedding);
                if sim >= CLUSTER_SIMILARITY_FLOOR {
                    trace.hits = trace.hits.saturating_add(1);
                    if !trace.queries.iter().any(|q| q == trimmed_q) {
                        trace.queries.push(trimmed_q.to_owned());
                    }
                    if let Some(out) = deterministic_output {
                        trace.deterministic_output = Some(out.to_owned());
                    }
                    blend_and_normalize(&mut trace.embedding, &emb);
                    if trace.hits >= MIN_CONSOLIDATION_COUNT {
                        let shortcut = CompiledShortcut {
                            shortcut_id: format!("reflex.auto.{trimmed_act}"),
                            intent: trace.intent.clone(),
                            action_target: trace.action_target.clone(),
                            deterministic_output: trace.deterministic_output.clone(),
                            exemplars: trace.queries.clone(),
                            consolidated_hits: trace.hits,
                            promoted_to_fast_path: true,
                        };
                        if let Ok(mut comp_guard) = self.compiled.write() {
                            comp_guard.insert(shortcut.action_target.clone(), shortcut.clone());
                        }
                        return Some(shortcut);
                    }
                    return None;
                }
            }
        }

        if guard.len() >= MAX_TRACES {
            guard.remove(0);
        }

        guard.push(SlowPathTrace {
            queries: vec![trimmed_q.to_owned()],
            intent: intent.to_owned(),
            action_target: trimmed_act.to_owned(),
            deterministic_output: deterministic_output.map(str::to_owned),
            embedding: emb,
            hits: 1,
        });

        None
    }

    #[must_use]
    pub fn resolve_compiled_output(&self, action_target: &str) -> Option<String> {
        let guard = self.compiled.read().ok()?;
        guard
            .get(action_target)
            .and_then(|s| s.deterministic_output.clone())
    }

    #[must_use]
    pub fn compiled_count(&self) -> usize {
        self.compiled.read().map_or(0, |g| g.len())
    }
}
