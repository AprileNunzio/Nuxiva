use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Justification {
    pub rule_id: String,
    pub antecedent_beliefs: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BeliefNode {
    pub belief_id: String,
    pub proposition: String,
    pub is_valid: bool,
    pub confidence: f64,
    pub justifications: Vec<Justification>,
    pub timestamp_ms: f64,
    pub revision_history: Vec<String>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct JustificationTruthMaintenanceSystem {
    beliefs: BTreeMap<String, BeliefNode>,
    dependents: BTreeMap<String, BTreeSet<String>>,
    brier_scores: Vec<f64>,
}

impl JustificationTruthMaintenanceSystem {
    #[must_use]
    pub fn new() -> Self {
        Self {
            beliefs: BTreeMap::new(),
            dependents: BTreeMap::new(),
            brier_scores: Vec::new(),
        }
    }

    pub fn assert_fact(&mut self, belief_id: &str, proposition: &str, timestamp_ms: f64) {
        let node = BeliefNode {
            belief_id: belief_id.to_string(),
            proposition: proposition.to_string(),
            is_valid: true,
            confidence: 1.0,
            justifications: Vec::new(),
            timestamp_ms,
            revision_history: vec![format!("asserted_fact@{}", timestamp_ms)],
        };
        self.beliefs.insert(belief_id.to_string(), node);
    }

    pub fn assert_justified(
        &mut self,
        belief_id: &str,
        proposition: &str,
        rule_id: &str,
        antecedents: Vec<String>,
        timestamp_ms: f64,
    ) {
        for ant in &antecedents {
            self.dependents
                .entry(ant.clone())
                .or_default()
                .insert(belief_id.to_string());
        }

        let is_valid = antecedents
            .iter()
            .all(|ant| self.beliefs.get(ant).is_some_and(|b| b.is_valid));

        let just = Justification {
            rule_id: rule_id.to_string(),
            antecedent_beliefs: antecedents,
        };

        let node = BeliefNode {
            belief_id: belief_id.to_string(),
            proposition: proposition.to_string(),
            is_valid,
            confidence: if is_valid { 0.95 } else { 0.0 },
            justifications: vec![just],
            timestamp_ms,
            revision_history: vec![format!("justified@{}", timestamp_ms)],
        };
        self.beliefs.insert(belief_id.to_string(), node);
    }

    pub fn retract(&mut self, belief_id: &str, reason: &str, timestamp_ms: f64) -> Vec<String> {
        let mut retracted = Vec::new();
        let mut queue = vec![belief_id.to_string()];

        while let Some(current_id) = queue.pop() {
            if let Some(belief) = self.beliefs.get_mut(&current_id) {
                if belief.is_valid {
                    belief.is_valid = false;
                    belief.confidence = 0.0;
                    belief
                        .revision_history
                        .push(format!("retracted:{reason}@{timestamp_ms}"));
                    retracted.push(current_id.clone());

                    if let Some(deps) = self.dependents.get(&current_id) {
                        for dep in deps {
                            queue.push(dep.clone());
                        }
                    }
                }
            }
        }

        retracted
    }

    pub fn update_brier_score(
        &mut self,
        predicted_probability: f64,
        actual_outcome_binary: f64,
    ) -> f64 {
        let error = predicted_probability - actual_outcome_binary;
        let score = error * error;
        self.brier_scores.push(score);
        score
    }

    #[must_use]
    pub fn mean_brier_score(&self) -> f64 {
        if self.brier_scores.is_empty() {
            0.0
        } else {
            self.brier_scores.iter().sum::<f64>() / self.brier_scores.len() as f64
        }
    }

    #[must_use]
    pub fn is_belief_valid(&self, belief_id: &str) -> bool {
        self.beliefs.get(belief_id).is_some_and(|b| b.is_valid)
    }
}
