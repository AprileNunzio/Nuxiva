use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CoreKnowledgePriors {
    pub object_permanence_prior: f64,
    pub intuitive_contact_physics_prior: f64,
    pub approximate_numerosity_prior: f64,
    pub causal_contingency_prior: f64,
}

impl Default for CoreKnowledgePriors {
    fn default() -> Self {
        Self {
            object_permanence_prior: 0.95,
            intuitive_contact_physics_prior: 0.90,
            approximate_numerosity_prior: 0.85,
            causal_contingency_prior: 0.80,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct OntogeneticBootstrapEngine {
    pub priors: CoreKnowledgePriors,
    pub developmental_stage: usize,
    pub cumulative_experience_ticks: u64,
}

impl Default for OntogeneticBootstrapEngine {
    fn default() -> Self {
        Self::new(CoreKnowledgePriors::default())
    }
}

impl OntogeneticBootstrapEngine {
    #[must_use]
    pub fn new(priors: CoreKnowledgePriors) -> Self {
        Self {
            priors,
            developmental_stage: 0,
            cumulative_experience_ticks: 0,
        }
    }

    pub fn tick(&mut self, interaction_entropy: f64) {
        self.cumulative_experience_ticks = self.cumulative_experience_ticks.saturating_add(1);
        if self.developmental_stage == 0 && self.cumulative_experience_ticks > 50 {
            self.developmental_stage = 1;
        } else if self.developmental_stage == 1
            && self.cumulative_experience_ticks > 150
            && interaction_entropy < 0.4
        {
            self.developmental_stage = 2;
        }
    }

    #[must_use]
    pub fn stage_description(&self) -> &'static str {
        match self.developmental_stage {
            0 => "sensorimotor_babbling",
            1 => "object_causal_discovery",
            _ => "symbol_grounding_and_concepts",
        }
    }
}
