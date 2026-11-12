use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct WorkspaceHypothesis {
    pub source_module: String,
    pub content_summary: String,
    pub saliency_weight: f64,
    pub precision_confidence: f64,
    pub vector_payload: Vec<f64>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct IgnitedBroadcast {
    pub winning_hypothesis: WorkspaceHypothesis,
    pub competition_entropy: f64,
    pub ignition_strength: f64,
    pub broadcast_timestamp_ticks: u64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GlobalWorkspace {
    pub ignition_threshold: f64,
    pub current_broadcast: Option<IgnitedBroadcast>,
    pub cycle_counter: u64,
}

impl Default for GlobalWorkspace {
    fn default() -> Self {
        Self::new(0.65)
    }
}

impl GlobalWorkspace {
    #[must_use]
    pub fn new(ignition_threshold: f64) -> Self {
        Self {
            ignition_threshold,
            current_broadcast: None,
            cycle_counter: 0,
        }
    }

    pub fn compete_and_ignite(
        &mut self,
        hypotheses: &[WorkspaceHypothesis],
    ) -> Option<IgnitedBroadcast> {
        self.cycle_counter = self.cycle_counter.saturating_add(1);
        if hypotheses.is_empty() {
            return None;
        }

        let mut scored: Vec<(f64, &WorkspaceHypothesis)> = hypotheses
            .iter()
            .map(|h| (h.saliency_weight * h.precision_confidence, h))
            .collect();

        scored.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal));
        let best = scored.first()?;

        let total_score: f64 = scored.iter().map(|(s, _)| *s).sum();
        let mut entropy = 0.0;
        if total_score > 1e-9 {
            for (s, _) in &scored {
                let p = *s / total_score;
                if p > 1e-9 {
                    entropy -= p * p.ln();
                }
            }
        }

        if best.0 >= self.ignition_threshold {
            let broadcast = IgnitedBroadcast {
                winning_hypothesis: best.1.clone(),
                competition_entropy: entropy,
                ignition_strength: best.0,
                broadcast_timestamp_ticks: self.cycle_counter,
            };
            self.current_broadcast = Some(broadcast.clone());
            Some(broadcast)
        } else {
            self.current_broadcast = None;
            None
        }
    }
}
