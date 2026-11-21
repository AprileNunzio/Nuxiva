use agency_domain::TaskId;
use agency_forge::{
    SandboxExecutionOutcome, ToolTestCase, diagnose_failure, inspect_tool_source,
    validate_tool_name, verify_sandbox_outcomes,
};
use agency_thought::{
    AlgorithmicStrategy, ArchitectureCandidate, EpistemicHypothesis, EvaluationWeights,
    PolicyCandidate, ProbeFinding, SubTaskBlueprint, WorldTransition, evaluate_candidates,
    expand_task_node, interrogate_goal, recruit_specialists, select_minimal_free_energy_policy,
    synthesize_epistemic_plan,
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

    pub(crate) fn epistemic_synthesize(
        goal: &str,
        hypotheses: &[EpistemicHypothesis],
        findings: &[ProbeFinding],
        shared_contracts: &[String],
    ) -> Result<Value, AgencyError> {
        let plan = synthesize_epistemic_plan(goal, hypotheses, findings, shared_contracts)
            .map_err(|e| AgencyError::BadRequest(e.to_string()))?;
        Ok(serde_json::to_value(plan)?)
    }

    pub(crate) fn agi_observe_transition(
        &mut self,
        transition: &WorldTransition,
    ) -> Result<Value, AgencyError> {
        let (belief, goal) = self
            .agi_kernel
            .observe_transition(transition)
            .map_err(|e| AgencyError::BadRequest(e.to_string()))?;
        Ok(json!({
            "belief": belief,
            "intrinsic_goal": goal,
        }))
    }

    pub(crate) fn agi_select_policy(candidates: &[PolicyCandidate]) -> Result<Value, AgencyError> {
        let policies = select_minimal_free_energy_policy(candidates)
            .map_err(|e| AgencyError::BadRequest(e.to_string()))?;
        Ok(json!({ "policies": policies }))
    }

    pub(crate) fn agi_godel_upgrade(
        &mut self,
        candidate: AlgorithmicStrategy,
    ) -> Result<Value, AgencyError> {
        let verdict = self
            .agi_kernel
            .evaluate_godel_upgrade(candidate)
            .map_err(|e| AgencyError::BadRequest(e.to_string()))?;
        if verdict.upgraded {
            self.event(
                "agi.strategy.upgraded",
                json!({
                    "domain": verdict.domain_key,
                    "strategy": verdict.active_strategy_id,
                    "generation": verdict.active_generation,
                }),
            )?;
        }
        Ok(serde_json::to_value(verdict)?)
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

    pub(crate) fn forge_verify_sandbox(
        name: &str,
        version: u32,
        code: &str,
        expected_cases: &[ToolTestCase],
        outcomes: &[SandboxExecutionOutcome],
    ) -> Value {
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
        if let Err(err) = inspect_tool_source(code) {
            let diag = diagnose_failure(&err);
            return json!({
                "ok": false,
                "error": err.to_string(),
                "diagnosis": diag,
            });
        }
        match verify_sandbox_outcomes(&clean_name, version.max(1), code, expected_cases, outcomes) {
            Ok(proof) => json!({
                "ok": true,
                "name": clean_name,
                "call_name": format!("x_{clean_name}"),
                "proof": proof,
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
