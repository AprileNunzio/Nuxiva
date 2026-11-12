use nuxiva_update_core::{Pipeline, Revision, StageStatus};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use serde::Serialize;
use std::path::PathBuf;

const MAX_INPUT: usize = 16 * 1024 * 1024;

fn bounded(raw: &str) -> PyResult<&str> {
    if raw.len() > MAX_INPUT {
        return Err(PyValueError::new_err("update input too large"));
    }
    Ok(raw)
}

fn to_json<T: Serialize>(value: &T) -> PyResult<String> {
    serde_json::to_string(value).map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

fn stage_status(raw: &str) -> PyResult<StageStatus> {
    match raw {
        "running" => Ok(StageStatus::Running),
        "done" => Ok(StageStatus::Done),
        "skipped" => Ok(StageStatus::Skipped),
        "failed" => Ok(StageStatus::Failed),
        _ => Err(PyValueError::new_err("invalid stage status")),
    }
}

#[pyfunction]
pub fn update_valid_rev(rev: &str) -> bool {
    Revision::parse(rev).is_ok()
}

#[pyfunction]
pub fn update_signature(raw: &str, exit_code: i32) -> PyResult<String> {
    to_json(&nuxiva_update_core::evaluate(bounded(raw)?, exit_code))
}

#[pyfunction]
pub fn update_verify_tree(py: Python<'_>, root: &str, ls_tree_z: &str) -> PyResult<String> {
    let entries = nuxiva_update_core::parse_ls_tree(bounded(ls_tree_z)?);
    let root = PathBuf::from(root);
    let report = py.detach(|| nuxiva_update_core::verify(&root, &entries));
    to_json(&report)
}

#[pyfunction]
pub fn update_impact(name_status_z: &str) -> PyResult<String> {
    to_json(&nuxiva_update_core::analyze(bounded(name_status_z)?))
}

#[pyfunction]
pub fn update_changelog(log: &str) -> PyResult<String> {
    to_json(&nuxiva_update_core::parse_oneline(bounded(log)?))
}

#[pyfunction]
#[pyo3(signature = (state, stage, status, now))]
pub fn update_pipeline_advance(
    state: Option<&str>,
    stage: &str,
    status: &str,
    now: f64,
) -> PyResult<String> {
    let mut pipeline = match state {
        Some(raw) if !raw.is_empty() => serde_json::from_str::<Pipeline>(bounded(raw)?)
            .map_err(|e| PyValueError::new_err(e.to_string()))?,
        _ => Pipeline::default(),
    };
    pipeline
        .advance(stage, stage_status(status)?, now)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    to_json(&pipeline)
}
