use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields, default)]
pub struct PlannerPolicy {
    pub w_category: f32,
    pub w_importance: f32,
    pub w_urgency: f32,
    pub w_context: f32,
    pub w_freshness: f32,
    pub w_preference: f32,
    pub w_interaction: f32,
    pub w_cost: f32,
    pub w_age: f32,
    pub enter: f32,
    pub exit: f32,
    pub dwell_ms: u64,
    pub interaction_ms: u64,
    pub cap_conversation: u8,
    pub cap_project: u8,
    pub cap_ambient: u8,
    pub cap_wide: u8,
    pub stream_free: f32,
    pub max_candidates: usize,
}

impl Default for PlannerPolicy {
    fn default() -> Self {
        Self {
            w_category: 1.0,
            w_importance: 0.6,
            w_urgency: 0.8,
            w_context: 0.5,
            w_freshness: 0.2,
            w_preference: 1.0,
            w_interaction: 0.3,
            w_cost: 0.3,
            w_age: 0.5,
            enter: 0.5,
            exit: 0.3,
            dwell_ms: 8_000,
            interaction_ms: 60_000,
            cap_conversation: 3,
            cap_project: 6,
            cap_ambient: 4,
            cap_wide: 8,
            stream_free: 0.2,
            max_candidates: 256,
        }
    }
}

impl PlannerPolicy {
    #[must_use]
    pub fn valid(&self) -> bool {
        let weights = [
            self.w_category,
            self.w_importance,
            self.w_urgency,
            self.w_context,
            self.w_freshness,
            self.w_preference,
            self.w_interaction,
            self.w_cost,
            self.w_age,
            self.enter,
            self.exit,
            self.stream_free,
        ];
        weights
            .iter()
            .all(|w| w.is_finite() && (0.0..=10.0).contains(w))
            && self.exit <= self.enter
            && self.max_candidates <= 1024
    }
}
