use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

#[pyfunction]
pub fn holo_prepare(py: Python<'_>, raw: &str) -> PyResult<String> {
    let owned = raw.to_owned();
    py.detach(move || nuxiva_holo_core::prepare(&owned))
        .map_err(|err| PyValueError::new_err(err.code()))
}
