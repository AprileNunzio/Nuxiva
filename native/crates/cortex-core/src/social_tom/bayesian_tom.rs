use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

use crate::social_tom::agent_model::AgentMentalModel;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SallyAnneQuery {
    pub object_name: String,
    pub true_current_location: String,
    pub observer_agent_id: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SallyAnnePrediction {
    pub predicted_search_location: String,
    pub holds_false_belief: bool,
    pub confidence: f64,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct BayesianTheoryOfMindEngine {
    agent_models: BTreeMap<String, AgentMentalModel>,
}

impl BayesianTheoryOfMindEngine {
    #[must_use]
    pub fn new() -> Self {
        Self {
            agent_models: BTreeMap::new(),
        }
    }

    pub fn register_agent(&mut self, agent_id: &str, depth: usize) {
        self.agent_models
            .insert(agent_id.to_string(), AgentMentalModel::new(agent_id, depth));
    }

    pub fn update_agent_observation(
        &mut self,
        agent_id: &str,
        object: &str,
        observed_location: &str,
    ) {
        if let Some(agent) = self.agent_models.get_mut(agent_id) {
            agent.set_belief(object, observed_location);
            agent.set_perceptual_access(object, true);
        }
    }

    pub fn notify_world_change(
        &mut self,
        object: &str,
        new_location: &str,
        present_agents: &[&str],
    ) {
        for (agent_id, agent) in &mut self.agent_models {
            let is_present = present_agents.contains(&agent_id.as_str());
            if is_present {
                agent.set_belief(object, new_location);
                agent.set_perceptual_access(object, true);
            } else {
                agent.set_perceptual_access(object, false);
            }
        }
    }

    #[must_use]
    pub fn solve_sally_anne(&self, query: &SallyAnneQuery) -> SallyAnnePrediction {
        if let Some(agent) = self.agent_models.get(&query.observer_agent_id) {
            if let Some(believed_loc) = agent.get_belief(&query.object_name) {
                let holds_false_belief = believed_loc != query.true_current_location;
                return SallyAnnePrediction {
                    predicted_search_location: believed_loc.to_string(),
                    holds_false_belief,
                    confidence: 0.99,
                };
            }
        }

        SallyAnnePrediction {
            predicted_search_location: query.true_current_location.clone(),
            holds_false_belief: false,
            confidence: 0.50,
        }
    }

    #[must_use]
    pub fn infer_intention(
        &self,
        candidate_intentions: &[&str],
        observed_actions: &[&str],
    ) -> String {
        let mut best_intention = "idle".to_string();
        let mut best_score = f64::NEG_INFINITY;

        for &intent in candidate_intentions {
            let match_count = observed_actions
                .iter()
                .filter(|&&act| act.contains(intent) || intent.contains(act))
                .count();
            let score = match_count as f64;
            if score > best_score {
                best_score = score;
                best_intention = intent.to_string();
            }
        }

        best_intention
    }
}
