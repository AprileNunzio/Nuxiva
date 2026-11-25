use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

#[pyfunction]
pub fn holo_prepare(py: Python<'_>, raw: &str) -> PyResult<String> {
    let owned = raw.to_owned();
    py.detach(move || nuxiva_holo_core::prepare(&owned))
        .map_err(|err| PyValueError::new_err(err.code()))
}

#[pyfunction]
pub fn holo_dna(py: Python<'_>, sequence: &str) -> PyResult<String> {
    let owned = sequence.to_owned();
    py.detach(move || nuxiva_holo_core::dna::generate(&owned))
        .map_err(|err| PyValueError::new_err(err.code()))
}

#[pyfunction]
pub fn holo_inspect_glb(py: Python<'_>, data: &[u8]) -> PyResult<String> {
    let owned = data.to_vec();
    py.detach(move || nuxiva_holo_core::glb::inspect_json(&owned))
        .map_err(|err| PyValueError::new_err(err.code()))
}
