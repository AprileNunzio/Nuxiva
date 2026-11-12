use agency_domain::{ProjectId, ProjectStatus, ReviewCheckpoint, TaskId, TaskStatus};
use agency_scheduler::capacity;
use agency_scheduler::leases::{JobLease, Owner};
use serde_json::{Value, json};

use crate::engine::projects::settle;
use crate::engine::{Engine, now_ms};
use crate::error::AgencyError;
use crate::protocol::TaskAction;

const LEASE_DURATION_MS: u64 = 300_000;

#[derive(Debug, Clone, Copy)]
pub struct TaskUpdateArgs<'a> {
    pub action: TaskAction,
    pub feedback: Option<&'a str>,
    pub checkpoint: Option<&'a str>,
    pub worker: Option<&'a str>,
    pub generation: Option<u64>,
    pub tokens: u64,
    pub seconds: u64,
    pub proofs: &'a [crate::protocol::ProofSpec],
}

impl Engine {
    pub(crate) fn update_task(
        &mut self,
        id: &ProjectId,
        task: &TaskId,
        args: TaskUpdateArgs<'_>,
    ) -> Result<Value, AgencyError> {
        let mut state = self.state_mut(id)?.clone();
        let owner = Owner {
            tenant: "nuxiva".to_string(),
            account: id.as_str().to_string(),
        };
        let now = now_ms();
        if let Some(w) = args.worker {
            let generation_nr = args.generation.unwrap_or(0);
            if let Some(lease) = state.leases.get(task) {
                lease.validate(&owner, w, generation_nr, now).map_err(|e| {
                    AgencyError::BadRequest(format!("stale or revoked assignment: {e}"))
                })?;
            } else {
                return Err(AgencyError::BadRequest(
                    "no assignment found for task".to_string(),
                ));
            }
        }
        let review_cp = match (args.action, args.checkpoint) {
            (TaskAction::Submit, Some(cp)) => {
                let w = args.worker.unwrap_or("agent");
                let generation_nr = args.generation.unwrap_or(1);
                Some(ReviewCheckpoint::new(cp, w, generation_nr, now)?)
            }
            _ => None,
        };
        for p in args.proofs {
            let mut proof =
                agency_domain::Proof::new(&p.criterion, &p.command, &p.expected_output)?;
            if p.verified || p.actual_output.is_some() || p.artifact_hash.is_some() {
                proof.record_result(
                    p.actual_output.as_deref().unwrap_or(""),
                    p.artifact_hash.as_deref(),
                    p.verified,
                )?;
            }
            state.graph.update(task, |t| {
                t.add_proof(proof);
                Ok(())
            })?;
        }
        state
            .graph
            .update(task, |t| t.record_usage(args.tokens, args.seconds))?;
        state.project.record_usage(args.tokens, args.seconds)?;
        let outcome = state.graph.update(task, |t| match args.action {
            TaskAction::Submit => t.submit_with_checkpoint(review_cp),
            TaskAction::Approve => t.approve(),
            TaskAction::Rework => t.rework(args.feedback.unwrap_or("rework requested")),
            TaskAction::Fail => t.fail(),
            TaskAction::Cancel => t.cancel(),
            TaskAction::Interrupt => t.interrupt(),
        });
        let exhausted = matches!(
            outcome,
            Err(agency_planner::PlanError::Domain(
                agency_domain::DomainError::AttemptsExhausted
            ))
        );
        if !exhausted {
            outcome?;
        }
        if args.action == TaskAction::Approve {
            if let Some(lease) = state.leases.get_mut(task) {
                if let Some(w) = args.worker {
                    let generation_nr = args.generation.unwrap_or_else(|| lease.generation());
                    let _ = lease.complete(&owner, w, generation_nr, now);
                }
            }
        }
        let before = state.project.status();
        settle(&mut state)?;
        let after = state.project.status();
        let detail = state.detail();
        self.commit_state(id, state)?;
        self.event(
            args.action.event(),
            json!({ "project": id, "task": task, "tokens": args.tokens, "seconds": args.seconds }),
        )?;
        if before != after {
            self.event("project.status", json!({ "project": id, "status": after }))?;
        }
        Ok(detail)
    }

    pub(crate) fn revoke_assignment(
        &mut self,
        id: &ProjectId,
        task: &TaskId,
    ) -> Result<Value, AgencyError> {
        let mut state = self.state_mut(id)?.clone();
        let owner = Owner {
            tenant: "nuxiva".to_string(),
            account: id.as_str().to_string(),
        };
        if let Some(lease) = state.leases.get_mut(task) {
            lease
                .revoke(&owner)
                .map_err(|e| AgencyError::BadRequest(e.to_string()))?;
        }
        if state.graph.get(task).map(agency_domain::Task::status) == Some(TaskStatus::Running) {
            state.graph.update(task, agency_domain::Task::interrupt)?;
        }
        let detail = state.detail();
        self.commit_state(id, state)?;
        self.event("assignment.revoked", json!({ "project": id, "task": task }))?;
        Ok(detail)
    }

    pub(crate) fn validate_worker(
        &self,
        id: &ProjectId,
        worker: Option<&str>,
        generation: Option<u64>,
    ) -> Result<(), AgencyError> {
        let Some(worker) = worker else {
            return Ok(());
        };
        let generation_nr = generation.unwrap_or(0);
        let state = self.projects.get(id).ok_or(AgencyError::NotFound)?;
        let owner = Owner {
            tenant: "nuxiva".to_string(),
            account: id.as_str().to_string(),
        };
        let now = now_ms();
        let matched = state
            .leases
            .values()
            .any(|lease| lease.validate(&owner, worker, generation_nr, now).is_ok());
        if !matched {
            return Err(AgencyError::BadRequest(
                "worker assignment revoked, expired, or invalid".to_string(),
            ));
        }
        Ok(())
    }

    pub(crate) fn dispatch(&mut self) -> Result<Value, AgencyError> {
        let limit = usize::from(
            capacity(&self.host, &self.settings.model, &self.settings.scheduler).parallel_agents,
        );
        let mut room = limit.saturating_sub(self.running_total());
        let mut started = Vec::new();
        let ids: Vec<ProjectId> = self.projects.keys().cloned().collect();
        for id in ids {
            if room == 0 {
                break;
            }
            let state = self.state_mut(&id)?;
            if state.project.status() != ProjectStatus::Running || !state.project.within_budget() {
                continue;
            }
            let per_project = usize::from(state.project.budget().max_parallel());
            let picks: Vec<TaskId> = state
                .graph
                .dispatchable(per_project)
                .into_iter()
                .take(room)
                .cloned()
                .collect();
            let owner = Owner {
                tenant: "nuxiva".to_string(),
                account: id.as_str().to_string(),
            };
            let now = now_ms();
            for task in &picks {
                state.graph.update(task, agency_domain::Task::start)?;
                let job_lease = state
                    .leases
                    .entry(task.clone())
                    .or_insert_with(|| JobLease::new(owner.clone()));
                let worker_id = format!(
                    "agent-{}-g{}",
                    task,
                    job_lease.generation().saturating_add(1)
                );
                let lease = job_lease
                    .assign(&owner, worker_id, now, LEASE_DURATION_MS)
                    .map_err(|e| AgencyError::BadRequest(e.to_string()))?;
                started.push(json!({
                    "project": id,
                    "task": task,
                    "worker": lease.worker,
                    "generation": lease.generation,
                    "expires_at": lease.expires_at,
                }));
            }
            room = room.saturating_sub(picks.len());
            if !picks.is_empty() {
                self.persist(&id)?;
                self.event("task.started", json!({ "project": id, "tasks": picks }))?;
            }
        }
        Ok(json!({ "started": started, "capacity": limit }))
    }
}
