use capability_registry::Contract;
use reason_understand::Goal;
use serde::Serialize;
use serde_json::json;

use crate::catalog::render;

pub const PLAN_SCHEMA: &str = r#"{"type":"object","additionalProperties":false,"required":["steps"],"properties":{"steps":{"type":"array","minItems":1,"maxItems":12,"items":{"type":"object","additionalProperties":false,"required":["id"],"properties":{"id":{"type":"string","pattern":"^[a-z0-9_]{1,48}$"},"capability":{"type":["string","null"]},"missing_hint":{"type":["string","null"],"maxLength":240},"args":{"type":"object","additionalProperties":{"oneOf":[{"type":"object","additionalProperties":false,"required":["from","value"],"properties":{"from":{"const":"literal"},"value":{"type":"string"}}},{"type":"object","additionalProperties":false,"required":["from","step"],"properties":{"from":{"const":"step"},"step":{"type":"string"}}},{"type":"object","additionalProperties":false,"required":["from","role"],"properties":{"from":{"const":"entity"},"role":{"type":"string"}}}]}}}}}}}"#;

pub const PLAN_SYSTEM: &str = "You turn one Goal into the smallest plan that achieves it. Reply with a single JSON object that matches the schema and nothing else. Use only capabilities from CAPABILITIES, with exactly their input names. Pass user values by entity role, never retype them as literals, and chain outputs with from=step. When no listed capability can do a step, emit that step with capability=null and a short English missing_hint instead of inventing one. Never add effects the Goal does not list. At most 12 steps.";

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct PlanRequest {
    pub system: String,
    pub user: String,
    pub schema: &'static str,
    pub capabilities: Vec<String>,
}

#[must_use]
pub fn goal_shape(goal: &Goal) -> serde_json::Value {
    let entities: Vec<_> = goal
        .entities
        .iter()
        .map(|e| json!({ "role": e.role, "ty": e.ty, "source": e.source }))
        .collect();
    json!({
        "intent": goal.intent,
        "effects": goal.effects,
        "entities": entities,
        "constraints": goal.constraints,
        "risk": goal.risk,
    })
}

#[must_use]
pub fn build(goal: &Goal, contracts: &[&Contract], correction: Option<&str>) -> PlanRequest {
    let mut user = format!(
        "GOAL\n{}\n\nCAPABILITIES\n{}",
        goal_shape(goal),
        render(contracts)
    );
    if let Some(code) = correction {
        user.push_str("\n\nPREVIOUS PLAN REJECTED: ");
        user.push_str(code);
        user.push_str("\nFix only that problem.");
    }
    PlanRequest {
        system: PLAN_SYSTEM.to_owned(),
        user,
        schema: PLAN_SCHEMA,
        capabilities: contracts.iter().map(|c| c.id.clone()).collect(),
    }
}
