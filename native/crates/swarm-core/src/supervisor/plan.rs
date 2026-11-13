use std::collections::HashMap;

use nuxiva_agent_core::ceo::Decision;
use nuxiva_agent_core::ceo::words::{stem, stems};

use crate::catalog::{Catalog, WorkerTemplate};
use crate::error::{SwarmError, SwarmResult};
use crate::settings::{LevelBudget, Settings};
use crate::wire::{Ident, Level, Plan, SCHEMA_VERSION, Step, StepBudget, TaskEnvelope, VerifySpec};

#[must_use]
pub fn level_budget(settings: &Settings, level: Level) -> LevelBudget {
    let levels = &settings.levels;
    [
        (Level::Lampo, levels.lampo),
        (Level::Standard, levels.standard),
        (Level::Progetto, levels.progetto),
    ]
    .into_iter()
    .find_map(|(l, b)| (l == level).then_some(b))
    .unwrap_or(levels.standard)
}

#[must_use]
pub fn pick_intent(template: &WorkerTemplate, text: &str) -> Option<Ident> {
    let wanted = stems(text);
    let mut best: Option<(usize, &Ident)> = None;
    for intent in &template.intents {
        let score = intent
            .as_str()
            .split(['_', '.', ':', '-'])
            .filter(|word| !word.is_empty() && wanted.contains(&stem(word)))
            .count();
        if best.is_none_or(|(top, _)| score > top) {
            best = Some((score, intent));
        }
    }
    best.map(|(_, intent)| intent.clone())
}

fn share(total: u64, parts: usize) -> u64 {
    let parts = u64::try_from(parts).unwrap_or(u64::MAX).max(1);
    total.checked_div(parts).unwrap_or(1).max(1)
}

pub fn deterministic(
    catalog: &Catalog,
    settings: &Settings,
    task: &TaskEnvelope,
    decision: &Decision,
    text: &str,
) -> SwarmResult<Plan> {
    let mut agents: Vec<&str> = vec![decision.primary.as_str()];
    for id in &decision.secondaries {
        if !agents.contains(&id.as_str()) && catalog.template(&Ident::new(id)?).is_some() {
            agents.push(id.as_str());
        }
    }
    let count = agents.len();
    let mut steps = Vec::with_capacity(count);
    for (position, agent) in agents.into_iter().enumerate() {
        let template = catalog
            .template(&Ident::new(agent)?)
            .ok_or(SwarmError::UnknownTemplate)?;
        let intent = if position == 0 {
            task.intent.clone()
        } else {
            pick_intent(template, text).ok_or(SwarmError::UnknownIntent)?
        };
        let verify = match (task.constraints.level, position) {
            (Level::Standard, 0) => VerifySpec::Judge,
            (Level::Lampo | Level::Standard, _) => VerifySpec::None,
            (Level::Progetto, _) => VerifySpec::Evidence,
        };
        steps.push(Step {
            id: Ident::new(&format!("s{}", position.saturating_add(1)))?,
            worker_template: template.agent.clone(),
            intent,
            goal_ref: task.input.clone(),
            needs_graph: template.needs_graph,
            budget: StepBudget {
                tokens: share(task.constraints.tokens_max, count).min(template.tokens_max),
                tool_calls: share(task.constraints.tool_calls_max, count)
                    .min(template.tool_calls_max),
                time_ms: task.constraints.deadline_ms.min(template.time_ms),
            },
            verify,
        });
    }
    let plan = Plan {
        schema_version: SCHEMA_VERSION,
        id: Ident::new(&format!("p-{}", task.id.as_str()))?,
        steps,
        edges: Vec::new(),
    };
    check_budget(&plan, task)?;
    catalog.check_plan(&plan, settings)?;
    Ok(plan)
}

#[must_use]
pub fn critical_path_ms(plan: &Plan) -> Option<u64> {
    let index: HashMap<&str, usize> = plan
        .steps
        .iter()
        .enumerate()
        .map(|(i, s)| (s.id.as_str(), i))
        .collect();
    let mut incoming: Vec<Vec<usize>> = vec![Vec::new(); plan.steps.len()];
    for edge in &plan.edges {
        let (from, to) = (
            *index.get(edge.from.as_str())?,
            *index.get(edge.to.as_str())?,
        );
        incoming.get_mut(to)?.push(from);
    }
    let mut finish: Vec<Option<u64>> = vec![None; plan.steps.len()];
    for _ in 0..plan.steps.len() {
        for (i, step) in plan.steps.iter().enumerate() {
            if finish.get(i).copied().flatten().is_some() {
                continue;
            }
            let deps = incoming.get(i)?;
            let start = deps
                .iter()
                .map(|d| finish.get(*d).copied().flatten())
                .try_fold(0_u64, |acc, f| f.map(|v| acc.max(v)));
            if let Some(start) = start {
                *finish.get_mut(i)? = Some(start.saturating_add(step.budget.time_ms));
            }
        }
    }
    finish
        .into_iter()
        .try_fold(0_u64, |acc, f| f.map(|v| acc.max(v)))
}

pub fn check_budget(plan: &Plan, task: &TaskEnvelope) -> SwarmResult<()> {
    let tokens = plan
        .steps
        .iter()
        .fold(0_u64, |acc, s| acc.saturating_add(s.budget.tokens));
    let calls = plan
        .steps
        .iter()
        .fold(0_u64, |acc, s| acc.saturating_add(s.budget.tool_calls));
    let time = critical_path_ms(plan).ok_or(SwarmError::Cycle)?;
    let c = &task.constraints;
    if tokens <= c.tokens_max && calls <= c.tool_calls_max && time <= c.deadline_ms {
        Ok(())
    } else {
        Err(SwarmError::Budget)
    }
}
