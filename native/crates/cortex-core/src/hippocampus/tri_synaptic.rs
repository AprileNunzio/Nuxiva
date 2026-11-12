use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EpisodicMemoryNode {
    pub episode_id: String,
    pub timestamp_ms: f64,
    pub state_embedding: Vec<f32>,
    pub cause: String,
    pub effect: String,
    pub emotion_valence: f64,
    pub surprise_score: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DentateGyrusPatternSeparator {
    dense_dim: usize,
    sparse_dim: usize,
    projection_weights: Vec<f32>,
    top_k: usize,
}

impl DentateGyrusPatternSeparator {
    #[must_use]
    pub fn new(dense_dim: usize, sparse_dim: usize, top_k: usize) -> Self {
        let total = sparse_dim.saturating_mul(dense_dim);
        let mut projection_weights = Vec::with_capacity(total);
        for i in 0..total {
            let pseudo = ((i.saturating_mul(1_103_515_245).saturating_add(12345)) % 2000) as f32
                / 1000.0
                - 1.0;
            projection_weights.push(pseudo);
        }
        Self {
            dense_dim,
            sparse_dim,
            projection_weights,
            top_k,
        }
    }

    #[must_use]
    pub fn separate_pattern(&self, dense_input: &[f32]) -> Vec<f32> {
        let mut activations: Vec<(usize, f32)> = Vec::with_capacity(self.sparse_dim);
        for s in 0..self.sparse_dim {
            let mut sum = 0.0f32;
            for (d, &inp) in dense_input.iter().enumerate().take(self.dense_dim) {
                let w_idx = s.saturating_mul(self.dense_dim).saturating_add(d);
                let w = self.projection_weights.get(w_idx).copied().unwrap_or(0.0);
                sum += inp * w;
            }
            activations.push((s, sum));
        }

        activations.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

        let mut sparse = vec![0.0f32; self.sparse_dim];
        for &(idx, val) in activations.iter().take(self.top_k) {
            if val > 0.0 {
                if let Some(slot) = sparse.get_mut(idx) {
                    *slot = val;
                }
            }
        }
        sparse
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ModernHopfieldCA3 {
    stored_patterns: Vec<Vec<f32>>,
    pattern_dim: usize,
    beta: f32,
}

impl ModernHopfieldCA3 {
    #[must_use]
    pub fn new(pattern_dim: usize, beta: f32) -> Self {
        Self {
            stored_patterns: Vec::new(),
            pattern_dim,
            beta,
        }
    }

    pub fn store(&mut self, pattern: Vec<f32>) {
        if pattern.len() == self.pattern_dim {
            self.stored_patterns.push(pattern);
        }
    }

    #[must_use]
    pub fn energy(&self, query: &[f32]) -> f32 {
        if self.stored_patterns.is_empty() || query.len() != self.pattern_dim {
            return 0.0;
        }

        let mut max_dot = f32::NEG_INFINITY;
        let mut dots = Vec::with_capacity(self.stored_patterns.len());
        for pat in &self.stored_patterns {
            let mut dot = 0.0f32;
            for (p_val, q_val) in pat.iter().zip(query.iter()) {
                dot += *p_val * *q_val;
            }
            if dot > max_dot {
                max_dot = dot;
            }
            dots.push(dot);
        }

        let mut sum_exp = 0.0f32;
        for &dot in &dots {
            sum_exp += (self.beta * (dot - max_dot)).exp();
        }
        let lse = max_dot + (1.0 / self.beta) * sum_exp.ln();

        let mut norm_sq = 0.0f32;
        for &x in query {
            norm_sq += x * x;
        }

        -lse + 0.5 * norm_sq
    }

    #[must_use]
    pub fn complete_pattern(&self, query: &[f32], iterations: usize) -> Vec<f32> {
        if self.stored_patterns.is_empty() || query.len() != self.pattern_dim {
            return query.to_vec();
        }

        let mut state = query.to_vec();
        for _ in 0..iterations {
            let mut dots = Vec::with_capacity(self.stored_patterns.len());
            let mut max_dot = f32::NEG_INFINITY;
            for pat in &self.stored_patterns {
                let mut dot = 0.0f32;
                for (p_val, s_val) in pat.iter().zip(state.iter()) {
                    dot += *p_val * *s_val;
                }
                if dot > max_dot {
                    max_dot = dot;
                }
                dots.push(dot);
            }

            let mut weights = Vec::with_capacity(self.stored_patterns.len());
            let mut weight_sum = 0.0f32;
            for &dot in &dots {
                let w = (self.beta * (dot - max_dot)).exp();
                weights.push(w);
                weight_sum += w;
            }

            let mut next_state = vec![0.0f32; self.pattern_dim];
            if weight_sum > 1e-9 {
                for (idx, pat) in self.stored_patterns.iter().enumerate() {
                    let weight_val = weights.get(idx).copied().unwrap_or(0.0);
                    let norm_w = weight_val / weight_sum;
                    for (ns, &pv) in next_state.iter_mut().zip(pat.iter()) {
                        *ns += norm_w * pv;
                    }
                }
            }
            state = next_state;
        }
        state
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TriSynapticHippocampus {
    pub dentate_gyrus: DentateGyrusPatternSeparator,
    pub ca3_hopfield: ModernHopfieldCA3,
    pub episodic_graph: BTreeMap<String, EpisodicMemoryNode>,
}

impl TriSynapticHippocampus {
    #[must_use]
    pub fn new(dense_dim: usize, sparse_dim: usize, beta: f32) -> Self {
        Self {
            dentate_gyrus: DentateGyrusPatternSeparator::new(dense_dim, sparse_dim, 32),
            ca3_hopfield: ModernHopfieldCA3::new(dense_dim, beta),
            episodic_graph: BTreeMap::new(),
        }
    }

    pub fn encode_and_store_episode(
        &mut self,
        episode_id: &str,
        timestamp_ms: f64,
        embedding: Vec<f32>,
        cause: &str,
        effect: &str,
        surprise: f64,
    ) {
        self.ca3_hopfield.store(embedding.clone());
        let node = EpisodicMemoryNode {
            episode_id: episode_id.to_string(),
            timestamp_ms,
            state_embedding: embedding,
            cause: cause.to_string(),
            effect: effect.to_string(),
            emotion_valence: 0.0,
            surprise_score: surprise,
        };
        self.episodic_graph.insert(episode_id.to_string(), node);
    }

    #[must_use]
    pub fn generative_replay_high_surprise(
        &self,
        surprise_threshold: f64,
    ) -> Vec<EpisodicMemoryNode> {
        self.episodic_graph
            .values()
            .filter(|node| node.surprise_score >= surprise_threshold)
            .cloned()
            .collect()
    }
}
