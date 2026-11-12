use crate::candidate::Candidate;
use crate::policy::PlannerPolicy;
use serde::{Deserialize, Serialize};

pub const PREFERENCE_LIMIT: f32 = 0.3;

#[derive(Debug, Clone, Copy, PartialEq, Default, Serialize, Deserialize)]
pub struct Parts {
    pub category: f32,
    pub importance: f32,
    pub urgency: f32,
    pub context: f32,
    pub freshness: f32,
    pub preference: f32,
    pub interaction: f32,
    pub cost: f32,
    pub age: f32,
}

impl Parts {
    #[must_use]
    pub fn total(&self) -> f32 {
        self.category
            + self.importance
            + self.urgency
            + self.context
            + self.freshness
            + self.preference
            + self.interaction
            - self.cost
            - self.age
    }
}

fn unit(value: f32) -> f32 {
    if value.is_finite() {
        value.clamp(0.0, 1.0)
    } else {
        0.0
    }
}

#[allow(clippy::cast_precision_loss)]
fn ratio(a: u64, b: u64) -> f32 {
    if b == 0 {
        1.0
    } else {
        (a as f32 / b as f32).min(4.0)
    }
}

#[must_use]
pub fn score(c: &Candidate, budget: f32, policy: &PlannerPolicy) -> Parts {
    let preference = if c.preference.is_finite() {
        c.preference.clamp(-PREFERENCE_LIMIT, PREFERENCE_LIMIT)
    } else {
        0.0
    };
    let budget = if budget.is_finite() && budget > 0.0 {
        budget
    } else {
        1.0
    };
    let cost = if c.cost.is_finite() {
        c.cost.max(0.0)
    } else {
        budget
    };
    let (freshness, age) = match c.ttl_ms {
        Some(ttl) if ttl > 0 => {
            let r = ratio(c.age_ms, ttl);
            (unit(1.0 - r), (r - 1.0).max(0.0))
        }
        _ => (0.5, 0.0),
    };
    let interacted = c.interacted_ms.is_some_and(|ms| ms < policy.interaction_ms);
    Parts {
        category: policy.w_category * c.category().weight(),
        importance: policy.w_importance * f32::from(c.importance.min(100)) / 100.0,
        urgency: policy.w_urgency * f32::from(c.urgency.min(3)) / 3.0,
        context: policy.w_context * unit(c.relevance),
        freshness: policy.w_freshness * freshness,
        preference: policy.w_preference * preference,
        interaction: if interacted {
            policy.w_interaction
        } else {
            0.0
        },
        cost: policy.w_cost * (cost / budget).min(4.0),
        age: policy.w_age * age,
    }
}
