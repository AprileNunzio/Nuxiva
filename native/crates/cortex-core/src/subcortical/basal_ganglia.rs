use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CandidateAction {
    pub id: String,
    pub expected_reward: f64,
    pub risk_estimate: f64,
    pub payload: Vec<f64>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BasalGangliaDecision {
    pub selected_action: Option<CandidateAction>,
    pub stn_conflict_brake_active: bool,
    pub d1_go_activation: f64,
    pub d2_no_go_activation: f64,
    pub thalamic_disinhibition_score: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BasalGangliaGating {
    pub d1_weight: f64,
    pub d2_weight: f64,
    pub conflict_entropy_threshold: f64,
}

impl Default for BasalGangliaGating {
    fn default() -> Self {
        Self {
            d1_weight: 1.0,
            d2_weight: 1.1,
            conflict_entropy_threshold: 0.85,
        }
    }
}

impl BasalGangliaGating {
    #[must_use]
    pub fn new(d1_weight: f64, d2_weight: f64, conflict_entropy_threshold: f64) -> Self {
        Self {
            d1_weight,
            d2_weight,
            conflict_entropy_threshold,
        }
    }

    #[must_use]
    pub fn select_action(
        &self,
        candidates: &[CandidateAction],
        dopamine_tone: f64,
    ) -> BasalGangliaDecision {
        if candidates.is_empty() {
            return BasalGangliaDecision {
                selected_action: None,
                stn_conflict_brake_active: false,
                d1_go_activation: 0.0,
                d2_no_go_activation: 0.0,
                thalamic_disinhibition_score: 0.0,
            };
        }

        let mut scored_actions: Vec<(f64, f64, f64, &CandidateAction)> = Vec::new();
        for action in candidates {
            let d1 =
                action.expected_reward * (1.0 + dopamine_tone.clamp(-0.8, 2.0)) * self.d1_weight;
            let d2 = action.risk_estimate * (1.0 - dopamine_tone.clamp(-0.8, 0.8)) * self.d2_weight;
            let net_drive = d1 - d2;
            scored_actions.push((net_drive, d1, d2, action));
        }

        let max_drive = scored_actions
            .iter()
            .map(|(s, _, _, _)| *s)
            .fold(f64::NEG_INFINITY, f64::max);

        let exp_sum: f64 = scored_actions
            .iter()
            .map(|(s, _, _, _)| (s - max_drive).exp())
            .sum();

        let mut entropy = 0.0;
        for (s, _, _, _) in &scored_actions {
            let p = (s - max_drive).exp() / exp_sum;
            if p > 1e-9 {
                entropy -= p * p.ln();
            }
        }
        let max_possible_entropy = (scored_actions.len() as f64).ln().max(1e-6);
        let normalized_entropy = (entropy / max_possible_entropy).clamp(0.0, 1.0);

        if scored_actions.len() > 1 && normalized_entropy > self.conflict_entropy_threshold {
            return BasalGangliaDecision {
                selected_action: None,
                stn_conflict_brake_active: true,
                d1_go_activation: 0.0,
                d2_no_go_activation: 0.0,
                thalamic_disinhibition_score: 0.0,
            };
        }

        scored_actions.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal));
        let Some(best) = scored_actions.first() else {
            return BasalGangliaDecision {
                selected_action: None,
                stn_conflict_brake_active: false,
                d1_go_activation: 0.0,
                d2_no_go_activation: 0.0,
                thalamic_disinhibition_score: 0.0,
            };
        };

        if best.0 > 0.0 {
            BasalGangliaDecision {
                selected_action: Some(best.3.clone()),
                stn_conflict_brake_active: false,
                d1_go_activation: best.1,
                d2_no_go_activation: best.2,
                thalamic_disinhibition_score: best.0,
            }
        } else {
            BasalGangliaDecision {
                selected_action: None,
                stn_conflict_brake_active: false,
                d1_go_activation: best.1,
                d2_no_go_activation: best.2,
                thalamic_disinhibition_score: 0.0,
            }
        }
    }
}
