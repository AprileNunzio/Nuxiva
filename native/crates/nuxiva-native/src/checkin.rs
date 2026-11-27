use checkin_core::{Request, detect, plan};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

const MAX_TEXT_BYTES: usize = 600;
const MAX_NAMES: usize = 16;
const MAX_REQUEST_BYTES: usize = 64 * 1024;

fn invalid(error: impl std::fmt::Display) -> PyErr {
    PyValueError::new_err(error.to_string())
}

#[pyfunction]
fn checkin_detect(py: Python<'_>, text: &str, names_json: &str) -> PyResult<String> {
    if text.len() > MAX_TEXT_BYTES || names_json.len() > MAX_REQUEST_BYTES {
        return Err(PyValueError::new_err("checkin.too_large.text"));
    }
    let names: Vec<String> = serde_json::from_str(names_json).map_err(invalid)?;
    if names.len() > MAX_NAMES || names.iter().any(|n| n.len() > MAX_TEXT_BYTES) {
        return Err(PyValueError::new_err("checkin.too_large.names"));
    }
    let found = py.detach(|| detect(text, &names));
    serde_json::to_string(&found).map_err(invalid)
}

#[pyfunction]
fn checkin_plan(py: Python<'_>, request_json: &str) -> PyResult<String> {
    if request_json.len() > MAX_REQUEST_BYTES {
        return Err(PyValueError::new_err("checkin.too_large.request"));
    }
    let request: Request = serde_json::from_str(request_json).map_err(invalid)?;
    let chosen = py.detach(|| plan(&request)).map_err(invalid)?;
    serde_json::to_string(&chosen).map_err(invalid)
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(checkin_detect, m)?)?;
    m.add_function(wrap_pyfunction!(checkin_plan, m)?)?;
    Ok(())
}
