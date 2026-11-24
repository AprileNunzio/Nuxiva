use std::collections::{BTreeMap, BTreeSet};
use std::fmt;

use capability_registry::{Contract, Effect, Registry};
use reason_plan::{Arg, Plan, Step, Validated};
use reason_understand::Goal;

use crate::error::{ExecError, ExecResult};
use crate::journal::{Journal, Record, step_key};
use crate::outcome::{Report, Status, StepReport};
use crate::port::{ApprovalGate, Call, Cancel, Failure, Invoker};

pub const MAX_OUTPUT_BYTES: usize = 64 * 1024;
pub const MAX_ATTEMPTS: u8 = 3;

pub struct Executor<'a, I, A, J, C> {
    registry: &'a Registry,
    invoker: I,
    gate: A,
    journal: J,
    cancel: C,
}

impl<I, A, J, C> fmt::Debug for Executor<'_, I, A, J, C> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Executor").finish_non_exhaustive()
    }
}

impl<'a, I, A, J, C> Executor<'a, I, A, J, C>
where
    I: Invoker,
    A: ApprovalGate,
    J: Journal,
    C: Cancel,
{
    pub fn new(registry: &'a Registry, invoker: I, gate: A, journal: J, cancel: C) -> Self {
        Self {
            registry,
            invoker,
            gate,
            journal,
            cancel,
        }
    }

    pub fn journal(&self) -> &J {
        &self.journal
    }

    pub fn run(
        &mut self,
        plan: &Plan,
        validated: &Validated,
        goal: &Goal,
        plan_hash: &str,
    ) -> ExecResult<Report> {
        let steps: BTreeMap<&str, &Step> = plan.steps.iter().map(|s| (s.id.as_str(), s)).collect();
        let mut outputs: BTreeMap<String, String> = BTreeMap::new();
        let mut blocked: BTreeSet<String> = BTreeSet::new();
        let mut report = Report::default();
        for id in validated.order() {
            let step = steps
                .get(id)
                .ok_or_else(|| ExecError::UnknownStep(id.to_owned()))?;
            let status = self.step(step, validated, goal, plan_hash, &outputs, &mut blocked)?;
            if let Some(out) = status.0.output() {
                outputs.insert(step.id.clone(), out.to_owned());
            } else {
                blocked.insert(step.id.clone());
            }
            report.steps.push(StepReport {
                step: step.id.clone(),
                status: status.0,
                attempts: status.1,
            });
        }
        Ok(report)
    }

    fn step(
        &mut self,
        step: &Step,
        validated: &Validated,
        goal: &Goal,
        plan_hash: &str,
        outputs: &BTreeMap<String, String>,
        blocked: &mut BTreeSet<String>,
    ) -> ExecResult<(Status, u8)> {
        if self.cancel.cancelled() {
            return Ok((Status::Cancelled, 0));
        }
        let Some(capability) = &step.capability else {
            return Ok((Status::Missing, 0));
        };
        let depends_on_blocked = step
            .args
            .values()
            .any(|arg| matches!(arg, Arg::Step { step: dep } if blocked.contains(dep)));
        if depends_on_blocked {
            return Ok((Status::Skipped, 0));
        }
        let args = resolve(step, goal, outputs)?;
        let contract = self
            .registry
            .get(capability)
            .ok_or_else(|| ExecError::UnknownStep(step.id.clone()))?;
        let key = step_key(plan_hash, &step.id, &args);
        match self.journal.last(&key).cloned() {
            Some(Record::Succeeded(out)) => return Ok((Status::Replayed(out), 0)),
            Some(Record::Started) if has_side_effects(contract) && !contract.reversible => {
                return Ok((Status::Indeterminate, 0));
            }
            _ => {}
        }
        if validated.approvals.contains(&step.id) && !self.gate.approve(&step.id, capability, &args)
        {
            return Ok((Status::Denied, 0));
        }
        self.attempt(capability, &key, &args, contract)
    }

    fn attempt(
        &mut self,
        capability: &str,
        key: &str,
        args: &BTreeMap<String, String>,
        contract: &Contract,
    ) -> ExecResult<(Status, u8)> {
        let mut attempts = 0u8;
        loop {
            if self.cancel.cancelled() {
                return Ok((Status::Cancelled, attempts));
            }
            attempts = attempts.saturating_add(1);
            self.journal.append(key, Record::Started)?;
            let call = Call {
                capability,
                key,
                args,
            };
            match self.invoker.invoke(&call) {
                Ok(out) if out.len() <= MAX_OUTPUT_BYTES => {
                    self.journal.append(key, Record::Succeeded(out.clone()))?;
                    return Ok((Status::Done(out), attempts));
                }
                Ok(_) => {
                    self.journal.append(key, Record::Failed)?;
                    return Ok((Status::Failed, attempts));
                }
                Err(failure) => {
                    self.journal.append(key, Record::Failed)?;
                    let safe_to_repeat = match failure {
                        Failure::NotStarted => true,
                        Failure::Retryable => !has_side_effects(contract) || contract.reversible,
                        Failure::Permanent => false,
                    };
                    if !safe_to_repeat || attempts >= MAX_ATTEMPTS {
                        return Ok((Status::Failed, attempts));
                    }
                }
            }
        }
    }
}

fn has_side_effects(contract: &Contract) -> bool {
    contract.effects.iter().any(|e| *e != Effect::Read)
}

fn resolve(
    step: &Step,
    goal: &Goal,
    outputs: &BTreeMap<String, String>,
) -> ExecResult<BTreeMap<String, String>> {
    step.args
        .iter()
        .map(|(name, arg)| {
            let value = match arg {
                Arg::Literal { value } => value.clone(),
                Arg::Step { step: dep } => outputs
                    .get(dep)
                    .cloned()
                    .ok_or_else(|| ExecError::UnknownStep(dep.clone()))?,
                Arg::Entity { role } => goal
                    .entities
                    .iter()
                    .find(|e| &e.role == role)
                    .map(|e| e.value.clone())
                    .ok_or_else(|| ExecError::UnknownEntity(role.clone()))?,
            };
            Ok((name.clone(), value))
        })
        .collect()
}
