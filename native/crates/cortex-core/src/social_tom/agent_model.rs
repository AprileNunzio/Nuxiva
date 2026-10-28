use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AgentMentalModel {
    pub agent_id: String,
    pub beliefs: BTreeMap<String, String>,
    pub desires: Vec<String>,
    pub current_intention: Option<String>,
    pub epistemic_access_flags: BTreeMap<String, bool>,
    pub reputation_score: f64,
    pub recursive_depth: usize,
}

impl AgentMentalModel {
    #[must_use]
    pub fn new(agent_id: &str, recursive_depth: usize) -> Self {
        Self {
            agent_id: agent_id.to_string(),
            beliefs: BTreeMap::new(),
            desires: Vec::new(),
            current_intention: None,
            epistemic_access_flags: BTreeMap::new(),
            reputation_score: 0.8,
            recursive_depth,
        }
    }

    pub fn set_belief(&mut self, key: &str, value: &str) {
        self.beliefs.insert(key.to_string(), value.to_string());
    }

    #[must_use]
    pub fn get_belief(&self, key: &str) -> Option<&str> {
        self.beliefs.get(key).map(String::as_str)
    }

    pub fn set_perceptual_access(&mut self, entity_or_location: &str, has_access: bool) {
        self.epistemic_access_flags
            .insert(entity_or_location.to_string(), has_access);
    }

    #[must_use]
    pub fn has_perceptual_access(&self, entity_or_location: &str) -> bool {
        self.epistemic_access_flags
            .get(entity_or_location)
            .copied()
            .unwrap_or(false)
    }
}
