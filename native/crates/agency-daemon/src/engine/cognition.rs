use agency_domain::TaskId;
use agency_forge::{diagnose_failure, inspect_tool_source, validate_tool_name};
use agency_thought::{
    ArchitectureCandidate, EvaluationWeights, SubTaskBlueprint, evaluate_candidates,
    expand_task_node, interrogate_goal, recruit_specialists,
};
use serde_json::{Value, json};

use crate::engine::{Engine, project_id};
use crate::error::AgencyError;

impl Engine {
    pub(crate) fn thought_evaluate(
        candidates: &[ArchitectureCandidate],
    ) -> Result<Value, AgencyError> {
        let verdict = evaluate_candidates(candidates, EvaluationWeights::default())
            .map_err(|e| AgencyError::BadRequest(e.to_string()))?;
        Ok(serde_json::to_value(verdict)?)
    }

    pub(crate) fn socratic_interrogate(
        goal: &str,
        known_decisions: &[String],
    ) -> Result<Value, AgencyError> {
        let report = interrogate_goal(goal, known_decisions)
            .map_err(|e| AgencyError::BadRequest(e.to_string()))?;
        Ok(serde_json::to_value(report)?)
    }

    pub(crate) fn specialist_recruit(goal: &str, architecture: &str) -> Result<Value, AgencyError> {
        let roster = recruit_specialists(goal, architecture)
            .map_err(|e| AgencyError::BadRequest(e.to_string()))?;
        Ok(json!({ "specialists": roster }))
    }

    pub(crate) fn task_expand(
        &mut self,
        project: &str,
        task: &str,
        subtasks: &[SubTaskBlueprint],
    ) -> Result<Value, AgencyError> {
        let id = project_id(project)?;
        let _parent_id = TaskId::new(task)?;
        let mut state = self.state_mut(&id)?.clone();
        if state.project.status().is_terminal() {
            return Err(AgencyError::BadRequest("project is closed".to_owned()));
        }
        let expansion = expand_task_node(&mut state.graph, task, subtasks)
            .map_err(|e| AgencyError::BadRequest(e.to_string()))?;
        let detail = state.detail();
        self.commit_state(&id, state)?;
        self.event(
            "task.expanded",
            json!({
                "project": id,
                "parent_task": expansion.parent_task,
                "added_tasks": expansion.added_tasks,
            }),
        )?;
        Ok(json!({
            "expansion": expansion,
            "project": detail,
        }))
    }

    pub(crate) fn forge_inspect(name: &str, code: &str) -> Value {
        let clean_name = match validate_tool_name(name) {
            Ok(n) => n,
            Err(err) => {
                let diag = diagnose_failure(&err);
                return json!({
                    "ok": false,
                    "error": err.to_string(),
                    "diagnosis": diag,
                });
            }
        };
        match inspect_tool_source(code) {
            Ok(verdict) => json!({
                "ok": true,
                "name": clean_name,
                "call_name": format!("x_{clean_name}"),
                "verdict": verdict,
            }),
            Err(err) => {
                let diag = diagnose_failure(&err);
                json!({
                    "ok": false,
                    "error": err.to_string(),
                    "diagnosis": diag,
                })
            }
        }
    }
}
