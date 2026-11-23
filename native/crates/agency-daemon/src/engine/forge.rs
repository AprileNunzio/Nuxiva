use agency_domain::{ProjectId, TaskId};
use agency_forge::{Access, ForgeError, ForgedToolSpec, SandboxExecutionOutcome};
use agency_scheduler::leases::Owner;
use serde_json::{Value, json};

use crate::config::Config;
use crate::engine::{Engine, now_ms};
use crate::error::AgencyError;
use crate::files;
use crate::protocol::{AccessKind, AttemptRef, ForgeProposal};

const FORGE_FILE: &str = "forge.json";

fn forge_error(error: &ForgeError) -> AgencyError {
    AgencyError::BadRequest(error.to_string())
}

impl Engine {
    pub(crate) fn load_forge(config: &Config) -> Result<agency_forge::ForgeCatalog, AgencyError> {
        match files::read(&config.path(FORGE_FILE))? {
            Some(bytes) => Ok(serde_json::from_slice(&bytes)?),
            None => Ok(agency_forge::ForgeCatalog::new()),
        }
    }

    fn persist_forge(&self) -> Result<(), AgencyError> {
        files::write_atomic(
            &self.config.path(FORGE_FILE),
            &serde_json::to_vec(&self.forge)?,
        )
    }

    fn validate_attempt(&self, attempt: &AttemptRef) -> Result<(ProjectId, TaskId), AgencyError> {
        let id = ProjectId::new(&attempt.project)?;
        let task = TaskId::new(&attempt.task)?;
        let state = self.projects.get(&id).ok_or(AgencyError::NotFound)?;
        let owner = Owner {
            tenant: "nuxiva".to_owned(),
            account: id.as_str().to_owned(),
        };
        let valid = state.leases.get(&task).is_some_and(|lease| {
            lease
                .validate(&owner, &attempt.worker, attempt.generation, now_ms())
                .is_ok()
        });
        if !valid {
            return Err(AgencyError::BadRequest(
                "worker assignment revoked, expired, or invalid".to_owned(),
            ));
        }
        Ok((id, task))
    }

    pub(crate) fn forge_propose(
        &mut self,
        attempt: &AttemptRef,
        tool: ForgeProposal,
    ) -> Result<Value, AgencyError> {
        let (id, task) = self.validate_attempt(attempt)?;
        let spec = ForgedToolSpec {
            name: tool.name,
            description: tool.description,
            args_schema: tool.args_schema,
            code: tool.code,
            tests: tool.tests,
            project_id: id.as_str().to_owned(),
            task_id: task.as_str().to_owned(),
            permissions: tool.permissions,
        };
        let record = self.forge.propose(spec).map_err(|e| forge_error(&e))?;
        self.persist_forge()?;
        self.event(
            "forge.proposed",
            json!({ "project": id, "task": task, "tool": record.name, "version": record.version }),
        )?;
        Ok(json!({ "tool": record }))
    }

    pub(crate) fn forge_activate(
        &mut self,
        name: &str,
        outcomes: &[SandboxExecutionOutcome],
    ) -> Result<Value, AgencyError> {
        let (record, proof) = self
            .forge
            .verify_and_activate(name, outcomes)
            .map_err(|e| forge_error(&e))?;
        self.persist_forge()?;
        self.event(
            "forge.activated",
            json!({ "tool": record.name, "version": record.version, "digest": proof.digest }),
        )?;
        Ok(json!({ "tool": record, "proof": proof }))
    }

    pub(crate) fn forge_revoke(&mut self, name: &str, reason: &str) -> Result<Value, AgencyError> {
        let record = self
            .forge
            .revoke(name, reason)
            .map_err(|e| forge_error(&e))?;
        self.persist_forge()?;
        self.event("forge.revoked", json!({ "tool": record.name }))?;
        Ok(json!({ "tool": record }))
    }

    pub(crate) fn forge_authorize(
        &mut self,
        attempt: &AttemptRef,
        tool: &str,
        kind: AccessKind,
        target: &str,
    ) -> Result<Value, AgencyError> {
        let outcome = self.validate_attempt(attempt).and_then(|(id, task)| {
            let access = match kind {
                AccessKind::Read => Access::Read(target),
                AccessKind::Write => Access::Write(target),
                AccessKind::Network => Access::Network(target),
            };
            self.forge
                .authorize(tool, id.as_str(), task.as_str(), access)
                .map_err(|e| forge_error(&e))
        });
        if let Err(error) = &outcome {
            self.event(
                "forge.denied",
                json!({ "project": attempt.project, "task": attempt.task, "tool": tool, "reason": error.to_string() }),
            )?;
        }
        outcome?;
        Ok(json!({ "allowed": true }))
    }
}
