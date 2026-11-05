use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use serde_json::Value;

const MAX_DOCUMENT: usize = 8 * 1024 * 1024;

fn parse(raw: &str) -> PyResult<Value> {
    if raw.len() > MAX_DOCUMENT {
        return Err(PyValueError::new_err("display document too large"));
    }
    serde_json::from_str(raw).map_err(|e| PyValueError::new_err(e.to_string()))
}

#[pyfunction]
pub fn display_diff(old_json: &str, new_json: &str) -> PyResult<Option<String>> {
    let (old, new) = (parse(old_json)?, parse(new_json)?);
    nuxiva_display_stream::diff(&old, &new)
        .map(|ops| serde_json::to_string(&ops).map_err(|e| PyRuntimeError::new_err(e.to_string())))
        .transpose()
}

#[pyfunction]
pub fn display_apply(doc_json: &str, ops_json: &str) -> PyResult<String> {
    let mut doc = parse(doc_json)?;
    let ops: Vec<nuxiva_display_stream::Op> =
        serde_json::from_str(ops_json).map_err(|e| PyValueError::new_err(e.to_string()))?;
    nuxiva_display_stream::apply(&mut doc, &ops).map_err(|e| PyValueError::new_err(e.code()))?;
    serde_json::to_string(&doc).map_err(|e| PyRuntimeError::new_err(e.to_string()))
}
