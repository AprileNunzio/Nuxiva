use std::collections::{BTreeMap, BTreeSet};

use capability_registry::{Contract, Effect, Registry, Role, State, ValueType};
use reason_understand::{Goal, Source};

use crate::error::{PlanError, PlanResult};
use crate::plan::{Arg, MAX_STEPS, Plan, Step};

const RECIPIENT_TYPES: [ValueType; 2] = [ValueType::Contact, ValueType::Url];

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Validated {
    pub levels: Vec<Vec<String>>,
    pub missing: Vec<String>,
    pub approvals: Vec<String>,
}

impl Validated {
    #[must_use]
    pub fn order(&self) -> Vec<&str> {
        self.levels.iter().flatten().map(String::as_str).collect()
    }
}

fn contract_of<'a>(
    registry: &'a Registry,
    role: Role,
    step: &Step,
) -> PlanResult<Option<&'a Contract>> {
    let Some(id) = &step.capability else {
        return Ok(None);
    };
    let contract = registry
        .get(id)
        .ok_or_else(|| PlanError::UnknownCapability(id.clone()))?;
    if contract.state != State::Active || !role.permits(contract.min_role) {
        return Err(PlanError::RoleDenied(id.clone()));
    }
    Ok(Some(contract))
}

fn dependencies(step: &Step) -> BTreeSet<&str> {
    step.args
        .values()
        .filter_map(|arg| match arg {
            Arg::Step { step } => Some(step.as_str()),
            _ => None,
        })
        .collect()
}

fn levels(plan: &Plan) -> PlanResult<Vec<Vec<String>>> {
    let mut remaining: BTreeMap<&str, BTreeSet<&str>> = plan
        .steps
        .iter()
        .map(|s| (s.id.as_str(), dependencies(s)))
        .collect();
    let mut out = Vec::new();
    while !remaining.is_empty() {
        let ready: Vec<&str> = remaining
            .iter()
            .filter(|(_, deps)| deps.is_empty())
            .map(|(id, _)| *id)
            .collect();
        if ready.is_empty() {
            return Err(PlanError::Cycle);
        }
        for id in &ready {
            remaining.remove(id);
        }
        for deps in remaining.values_mut() {
            for id in &ready {
                deps.remove(id);
            }
        }
        out.push(ready.into_iter().map(str::to_owned).collect());
    }
    Ok(out)
}

fn check_arg(
    step: &Step,
    input: &str,
    expected: ValueType,
    arg: &Arg,
    goal: &Goal,
    produced: &BTreeMap<&str, Option<ValueType>>,
) -> PlanResult<()> {
    let mismatch = || PlanError::TypeMismatch {
        step: step.id.clone(),
        input: input.to_owned(),
    };
    match arg {
        Arg::Literal { .. } => {
            if RECIPIENT_TYPES.contains(&expected) {
                return Err(PlanError::ExternalTarget {
                    step: step.id.clone(),
                });
            }
            Ok(())
        }
        Arg::Step { step: from } => match produced.get(from.as_str()) {
            Some(Some(ty)) if *ty == expected => Ok(()),
            Some(Some(_)) => Err(mismatch()),
            Some(None) => Ok(()),
            None => Err(PlanError::UnknownStep(from.clone())),
        },
        Arg::Entity { role } => {
            let entity = goal
                .entities
                .iter()
                .find(|e| &e.role == role)
                .ok_or_else(|| PlanError::UnknownEntity {
                    step: step.id.clone(),
                    role: role.clone(),
                })?;
            if entity.ty != expected {
                return Err(mismatch());
            }
            if RECIPIENT_TYPES.contains(&expected) && entity.source == Source::External {
                return Err(PlanError::ExternalTarget {
                    step: step.id.clone(),
                });
            }
            Ok(())
        }
    }
}

pub fn validate(
    plan: &Plan,
    registry: &Registry,
    role: Role,
    goal: &Goal,
) -> PlanResult<Validated> {
    if plan.steps.len() > MAX_STEPS {
        return Err(PlanError::TooManySteps);
    }
    let mut ids = BTreeSet::new();
    for step in &plan.steps {
        if !ids.insert(step.id.as_str()) {
            return Err(PlanError::DuplicateStep(step.id.clone()));
        }
    }
    for step in &plan.steps {
        for dep in dependencies(step) {
            if !ids.contains(dep) {
                return Err(PlanError::UnknownStep(dep.to_owned()));
            }
        }
    }
    let order = levels(plan)?;
    let mut produced: BTreeMap<&str, Option<ValueType>> = BTreeMap::new();
    let mut contracts: BTreeMap<&str, Option<&Contract>> = BTreeMap::new();
    for step in &plan.steps {
        let contract = contract_of(registry, role, step)?;
        produced.insert(step.id.as_str(), contract.map(|c| c.output));
        contracts.insert(step.id.as_str(), contract);
    }
    let mut missing = Vec::new();
    let mut approvals = Vec::new();
    for step in &plan.steps {
        let Some(Some(contract)) = contracts.get(step.id.as_str()) else {
            missing.push(step.id.clone());
            continue;
        };
        if !contract.effects.is_subset(&goal.effects) {
            return Err(PlanError::EffectNotRequested {
                step: step.id.clone(),
            });
        }
        for input in step.args.keys() {
            if !contract.inputs.iter().any(|p| &p.name == input) {
                return Err(PlanError::UnknownInput {
                    step: step.id.clone(),
                    input: input.clone(),
                });
            }
        }
        for param in &contract.inputs {
            match step.args.get(&param.name) {
                None if param.required => {
                    return Err(PlanError::MissingInput {
                        step: step.id.clone(),
                        input: param.name.clone(),
                    });
                }
                None => {}
                Some(arg) => check_arg(step, &param.name, param.ty, arg, goal, &produced)?,
            }
        }
        if contract.requires_approval() || contract.effects.contains(&Effect::Spend) {
            approvals.push(step.id.clone());
        }
    }
    Ok(Validated {
        levels: order,
        missing,
        approvals,
    })
}
