use nuxiva_devid_core::{Known, MAX_KNOWN, Seen, resolve};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use serde::Deserialize;

const MAX_INPUT: usize = 8 * 1024 * 1024;

#[derive(Deserialize)]
struct ResolveInput {
    known: Vec<Known>,
    seen: Seen,
}

#[pyfunction]
pub fn device_resolve(input_json: &str) -> PyResult<String> {
    if input_json.len() > MAX_INPUT {
        return Err(PyValueError::new_err("device input too large"));
    }
    let input: ResolveInput =
        serde_json::from_str(input_json).map_err(|e| PyValueError::new_err(e.to_string()))?;
    if input.known.len() > MAX_KNOWN {
        return Err(PyValueError::new_err("too many known devices"));
    }
    serde_json::to_string(&resolve(&input.known, &input.seen))
        .map_err(|e| PyRuntimeError::new_err(e.to_string()))
}
