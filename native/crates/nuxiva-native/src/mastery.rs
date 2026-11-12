use nuxiva_mastery_core::{Attempt, MAX_ATTEMPTS, evaluate};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;

const MAX_INPUT: usize = 64 * 1024;

#[pyfunction]
pub fn mastery_evaluate(attempts_json: &str, now: i64) -> PyResult<String> {
    if attempts_json.len() > MAX_INPUT {
        return Err(PyValueError::new_err("mastery input too large"));
    }
    let list: Vec<Attempt> =
        serde_json::from_str(attempts_json).map_err(|e| PyValueError::new_err(e.to_string()))?;
    if list.len() > MAX_ATTEMPTS.saturating_mul(2) {
        return Err(PyValueError::new_err("too many attempts"));
    }
    serde_json::to_string(&evaluate(&list, now)).map_err(|e| PyRuntimeError::new_err(e.to_string()))
}
