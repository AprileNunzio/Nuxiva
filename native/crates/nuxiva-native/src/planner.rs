use nuxiva_display_planner::PlannerPolicy;
use nuxiva_display_planner::plan::{Input, plan};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;

const MAX_INPUT: usize = 1024 * 1024;

#[pyfunction]
#[pyo3(signature = (input_json, policy_json = None))]
pub fn display_plan(input_json: &str, policy_json: Option<&str>) -> PyResult<String> {
    if input_json.len() > MAX_INPUT {
        return Err(PyValueError::new_err("planner input too large"));
    }
    let input: Input =
        serde_json::from_str(input_json).map_err(|e| PyValueError::new_err(e.to_string()))?;
    let policy: PlannerPolicy = match policy_json {
        Some(raw) => serde_json::from_str(raw).map_err(|e| PyValueError::new_err(e.to_string()))?,
        None => PlannerPolicy::default(),
    };
    let scene =
        plan(&input, &policy).map_err(|_| PyValueError::new_err("planner policy invalid"))?;
    serde_json::to_string(&scene).map_err(|e| PyRuntimeError::new_err(e.to_string()))
}
