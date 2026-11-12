use nuxiva_forma_core::{Plan, Traits, compile, compose, schema};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;

const MAX_INPUT: usize = 64 * 1024;

fn parts_json(plan: &Plan) -> PyResult<String> {
    let parts = compile(plan).map_err(|e| PyValueError::new_err(e.to_string()))?;
    serde_json::to_string(&serde_json::json!({ "parts": parts }))
        .map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

fn bounded(raw: &str) -> PyResult<&str> {
    if raw.len() > MAX_INPUT {
        Err(PyValueError::new_err("forma input too large"))
    } else {
        Ok(raw)
    }
}

#[pyfunction]
pub fn forma_compile(plan_json: &str) -> PyResult<String> {
    let plan: Plan = serde_json::from_str(bounded(plan_json)?)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    parts_json(&plan)
}

#[pyfunction]
pub fn forma_sculpt(traits_json: &str) -> PyResult<String> {
    let traits: Traits = serde_json::from_str(bounded(traits_json)?)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    parts_json(&compose(&traits))
}

#[pyfunction]
pub fn forma_schema() -> PyResult<String> {
    serde_json::to_string(&schema()).map_err(|e| PyRuntimeError::new_err(e.to_string()))
}
