use nuxiva_resource_core::plan_json;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

#[pyfunction]
pub fn resource_plan(py: Python<'_>, raw: &str) -> PyResult<String> {
    let owned = raw.to_owned();
    py.detach(move || plan_json(&owned))
        .map_err(|e| PyValueError::new_err(e.code()))
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(resource_plan, m)?)?;
    Ok(())
}
