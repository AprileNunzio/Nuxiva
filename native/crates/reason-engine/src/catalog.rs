use std::fmt::Write as _;

use capability_registry::{Contract, Effect, Registry, Role, ValueType};
use reason_understand::Goal;

pub const MAX_QUERY_BYTES: usize = 2_048;

fn ty(value: ValueType) -> &'static str {
    match value {
        ValueType::Text => "text",
        ValueType::Number => "number",
        ValueType::Bool => "bool",
        ValueType::File => "file",
        ValueType::Url => "url",
        ValueType::Contact => "contact",
        ValueType::Image => "image",
        ValueType::Json => "json",
        ValueType::Time => "time",
    }
}

fn effect(value: Effect) -> &'static str {
    match value {
        Effect::Read => "read",
        Effect::Write => "write",
        Effect::SendExternal => "send_external",
        Effect::Spend => "spend",
        Effect::Physical => "physical",
    }
}

fn clip(text: &str, max: usize) -> &str {
    if text.len() <= max {
        return text;
    }
    let mut end = max;
    while end > 0 && !text.is_char_boundary(end) {
        end = end.saturating_sub(1);
    }
    text.get(..end).unwrap_or_default()
}

#[must_use]
pub fn query(goal: &Goal, user_text: &str) -> String {
    let mut out = goal.intent.replace('_', " ");
    for entity in &goal.entities {
        out.push(' ');
        out.push_str(&entity.role.replace('_', " "));
    }
    for constraint in &goal.constraints {
        out.push(' ');
        out.push_str(constraint);
    }
    out.push(' ');
    out.push_str(user_text);
    clip(&out, MAX_QUERY_BYTES).to_owned()
}

#[must_use]
pub fn line(contract: &Contract) -> String {
    let mut out = format!("- {}(", contract.id);
    for (index, param) in contract.inputs.iter().enumerate() {
        if index > 0 {
            out.push_str(", ");
        }
        let mark = if param.required { "" } else { "?" };
        let _ = write!(out, "{}{mark}:{}", param.name, ty(param.ty));
    }
    let effects: Vec<&str> = contract.effects.iter().map(|e| effect(*e)).collect();
    let _ = write!(
        out,
        ") -> {} [{}]: {}",
        ty(contract.output),
        effects.join(","),
        contract.summary
    );
    out
}

#[must_use]
pub fn retrieve<'a>(
    registry: &'a Registry,
    goal: &Goal,
    user_text: &str,
    role: Role,
    limit: usize,
) -> Vec<&'a Contract> {
    registry
        .retrieve(&query(goal, user_text), limit, role)
        .into_iter()
        .filter_map(|hit| registry.get(&hit.id))
        .filter(|c| c.effects.is_subset(&goal.effects))
        .collect()
}

#[must_use]
pub fn render(contracts: &[&Contract]) -> String {
    contracts
        .iter()
        .map(|c| line(c))
        .collect::<Vec<_>>()
        .join("\n")
}
