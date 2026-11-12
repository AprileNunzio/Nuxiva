use agency_action::{
    ActionItem, ReplacementChunk, apply_surgical_patches, plan_parallel_batch, view_line_range,
};
use agency_codeindex::extract_outline;
use agency_forge::{diagnose_failure, inspect_tool_source, validate_tool_name};
use agency_thought::{
    ArchitectureCandidate, EvaluationWeights, evaluate_candidates, interrogate_goal,
    recruit_specialists,
};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use serde_json::json;

#[pyclass]
#[derive(Debug, Default)]
pub struct RustAgencyCore;

#[pymethods]
impl RustAgencyCore {
    #[new]
    #[must_use]
    pub fn new() -> Self {
        Self
    }

    #[allow(clippy::unused_self)]
    pub fn evaluate_candidates_json(&self, candidates_json: &str) -> PyResult<String> {
        let candidates: Vec<ArchitectureCandidate> = serde_json::from_str(candidates_json)
            .map_err(|e| PyValueError::new_err(format!("invalid candidates json: {e}")))?;
        let verdict = evaluate_candidates(&candidates, EvaluationWeights::default())
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        serde_json::to_string(&verdict).map_err(|e| PyValueError::new_err(e.to_string()))
    }

    #[allow(clippy::unused_self, clippy::needless_pass_by_value)]
    pub fn interrogate_goal_json(
        &self,
        goal: &str,
        known_decisions: Vec<String>,
    ) -> PyResult<String> {
        let report = interrogate_goal(goal, &known_decisions)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        serde_json::to_string(&report).map_err(|e| PyValueError::new_err(e.to_string()))
    }

    #[allow(clippy::unused_self)]
    pub fn recruit_specialists_json(&self, goal: &str, architecture: &str) -> PyResult<String> {
        let roster = recruit_specialists(goal, architecture)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        serde_json::to_string(&roster).map_err(|e| PyValueError::new_err(e.to_string()))
    }

    #[allow(clippy::unused_self)]
    pub fn outline_source_json(&self, path: &str, content: &str) -> PyResult<String> {
        let outline = extract_outline(path, content);
        serde_json::to_string(&outline).map_err(|e| PyValueError::new_err(e.to_string()))
    }

    #[allow(clippy::unused_self)]
    pub fn view_line_range_json(
        &self,
        content: &str,
        start_line: usize,
        end_line: usize,
    ) -> PyResult<String> {
        let view = view_line_range(content, start_line, end_line)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        serde_json::to_string(&view).map_err(|e| PyValueError::new_err(e.to_string()))
    }

    #[allow(clippy::unused_self)]
    pub fn apply_surgical_patches_json(
        &self,
        content: &str,
        chunks_json: &str,
    ) -> PyResult<String> {
        let chunks: Vec<ReplacementChunk> = serde_json::from_str(chunks_json)
            .map_err(|e| PyValueError::new_err(format!("invalid chunks json: {e}")))?;
        let outcome = apply_surgical_patches(content, &chunks)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        serde_json::to_string(&outcome).map_err(|e| PyValueError::new_err(e.to_string()))
    }

    #[allow(clippy::unused_self)]
    pub fn plan_parallel_batch_json(&self, actions_json: &str) -> PyResult<String> {
        let actions: Vec<ActionItem> = serde_json::from_str(actions_json)
            .map_err(|e| PyValueError::new_err(format!("invalid actions json: {e}")))?;
        let plan = plan_parallel_batch(&actions);
        serde_json::to_string(&plan).map_err(|e| PyValueError::new_err(e.to_string()))
    }

    #[allow(clippy::unused_self)]
    pub fn inspect_tool_source_json(&self, name: &str, code: &str) -> PyResult<String> {
        let clean_name = match validate_tool_name(name) {
            Ok(n) => n,
            Err(err) => {
                let diag = diagnose_failure(&err);
                return serde_json::to_string(&json!({
                    "ok": false,
                    "error": err.to_string(),
                    "diagnosis": diag,
                }))
                .map_err(|e| PyValueError::new_err(e.to_string()));
            }
        };
        let payload = match inspect_tool_source(code) {
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
        };
        serde_json::to_string(&payload).map_err(|e| PyValueError::new_err(e.to_string()))
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustAgencyCore>()?;
    Ok(())
}
