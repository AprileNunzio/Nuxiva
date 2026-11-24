use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::error::{PlanError, PlanResult};

pub const MAX_STEPS: usize = 12;
pub const MAX_PLAN_BYTES: usize = 32 * 1024;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "from", rename_all = "snake_case", deny_unknown_fields)]
pub enum Arg {
    Literal { value: String },
    Step { step: String },
    Entity { role: String },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Step {
    pub id: String,
    pub capability: Option<String>,
    #[serde(default)]
    pub missing_hint: Option<String>,
    #[serde(default)]
    pub args: BTreeMap<String, Arg>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Plan {
    pub steps: Vec<Step>,
}

pub fn slug(text: &str) -> bool {
    !text.is_empty()
        && text.len() <= 48
        && text
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_')
}

pub fn parse(raw: &str) -> PlanResult<Plan> {
    if raw.len() > MAX_PLAN_BYTES {
        return Err(PlanError::Invalid("too_large"));
    }
    let plan: Plan = serde_json::from_str(raw).map_err(|_| PlanError::Invalid("schema"))?;
    if plan.steps.is_empty() {
        return Err(PlanError::Invalid("empty"));
    }
    if plan.steps.len() > MAX_STEPS {
        return Err(PlanError::TooManySteps);
    }
    for step in &plan.steps {
        let named = slug(&step.id) && step.args.keys().all(|k| slug(k));
        let hinted = step
            .missing_hint
            .as_ref()
            .is_none_or(|h| h.len() <= 240 && !h.chars().any(char::is_control));
        let shaped = step.capability.is_some() != step.missing_hint.is_some();
        if !named || !hinted || !shaped {
            return Err(PlanError::Invalid("step"));
        }
    }
    Ok(plan)
}
