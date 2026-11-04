use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CapabilityDescriptor {
    pub capability_id: String,
    pub domain: String,
    pub verified_success_rate: f64,
    pub execution_cost_energy: f64,
    pub operational_limits: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GoalDescriptor {
    pub goal_id: String,
    pub description: String,
    pub priority: f64,
    pub satisfaction_level: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RelationshipModel {
    pub agent_id: String,
    pub trust_score: f64,
    pub cooperative_alignment: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct UncertaintyState {
    pub epistemic_uncertainty: f64,
    pub aleatoric_uncertainty: f64,
    pub total_entropy: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PersistentSelfModel {
    pub autobiographical_timeline: Vec<String>,
    pub capabilities: BTreeMap<String, CapabilityDescriptor>,
    pub body_schema_dof: usize,
    pub goals: Vec<GoalDescriptor>,
    pub relationships: BTreeMap<String, RelationshipModel>,
    pub uncertainty: UncertaintyState,
}

impl Default for PersistentSelfModel {
    fn default() -> Self {
        Self::new(34)
    }
}

impl PersistentSelfModel {
    #[must_use]
    pub fn new(body_schema_dof: usize) -> Self {
        Self {
            autobiographical_timeline: Vec::new(),
            capabilities: BTreeMap::new(),
            body_schema_dof,
            goals: Vec::new(),
            relationships: BTreeMap::new(),
            uncertainty: UncertaintyState {
                epistemic_uncertainty: 0.2,
                aleatoric_uncertainty: 0.1,
                total_entropy: 0.3,
            },
        }
    }

    pub fn record_autobiographical_event(&mut self, event: &str) {
        self.autobiographical_timeline.push(event.to_string());
    }

    pub fn register_capability(&mut self, id: &str, domain: &str, success_rate: f64, limits: &str) {
        self.capabilities.insert(
            id.to_string(),
            CapabilityDescriptor {
                capability_id: id.to_string(),
                domain: domain.to_string(),
                verified_success_rate: success_rate.clamp(0.0, 1.0),
                execution_cost_energy: 1.0,
                operational_limits: limits.to_string(),
            },
        );
    }

    #[must_use]
    pub fn can_perform(&self, capability_id: &str, min_confidence: f64) -> bool {
        self.capabilities
            .get(capability_id)
            .is_some_and(|cap| cap.verified_success_rate >= min_confidence)
    }
}
