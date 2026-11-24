use std::collections::BTreeSet;

use capability_registry::Effect as Declared;
use reason_eval::{Case, Effect, Outcome};
use reason_understand::{Goal, parse};

fn effects_of(goal: &Goal) -> BTreeSet<Effect> {
    goal.effects
        .iter()
        .map(|effect| match effect {
            Declared::Read => Effect::Read,
            Declared::Write => Effect::Write,
            Declared::SendExternal => Effect::SendExternal,
            Declared::Spend => Effect::Spend,
            Declared::Physical => Effect::Physical,
        })
        .collect()
}

#[must_use]
pub fn to_outcome(case: &Case, content: Option<&str>, tokens: u64, latency_ms: u64) -> Outcome {
    let goal = content.and_then(|raw| parse(raw, &case.text).ok());
    match goal {
        Some(goal) => Outcome {
            case_id: case.id.clone(),
            effects: effects_of(&goal),
            intent: goal.intent,
            completed: true,
            tokens,
            latency_ms,
        },
        None => Outcome {
            case_id: case.id.clone(),
            intent: String::new(),
            effects: BTreeSet::new(),
            completed: false,
            tokens,
            latency_ms,
        },
    }
}
