use crate::errors::poisoned;
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use std::sync::Mutex;

const MAX_REQUEST: usize = 256 * 1024;

#[pyfunction]
pub fn stage_plan(request_json: &str) -> PyResult<String> {
    if request_json.len() > MAX_REQUEST {
        return Err(PyValueError::new_err("stage request too large"));
    }
    let request: nuxiva_stage_core::PlanRequest =
        serde_json::from_str(request_json).map_err(|e| PyValueError::new_err(e.to_string()))?;
    serde_json::to_string(&nuxiva_stage_core::plan(&request))
        .map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

#[pyfunction]
pub fn particles_sample<'py>(
    py: Python<'py>,
    spec_json: &str,
    count: u32,
    seed: u64,
) -> PyResult<Bound<'py, PyBytes>> {
    if spec_json.len() > MAX_REQUEST {
        return Err(PyValueError::new_err("particle spec too large"));
    }
    let spec: nuxiva_stage_core::Spec =
        serde_json::from_str(spec_json).map_err(|e| PyValueError::new_err(e.to_string()))?;
    let cloud = nuxiva_stage_core::sample(&spec, count, seed)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    Ok(PyBytes::new(py, &nuxiva_stage_core::encode(&cloud)))
}

#[pyfunction]
pub fn particles_count(blob: &[u8]) -> PyResult<usize> {
    nuxiva_stage_core::decode(blob)
        .map(|cloud| cloud.len())
        .map_err(|e| PyValueError::new_err(e.to_string()))
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustParticleCache {
    inner: Mutex<nuxiva_stage_core::BlobCache>,
}

#[pymethods]
impl RustParticleCache {
    #[new]
    fn new(budget: usize) -> Self {
        Self {
            inner: Mutex::new(nuxiva_stage_core::BlobCache::new(budget)),
        }
    }

    fn get<'py>(&self, py: Python<'py>, key: &str) -> PyResult<Option<Bound<'py, PyBytes>>> {
        let mut guard = self.inner.lock().map_err(|_| poisoned())?;
        Ok(guard.get(key).map(|blob| PyBytes::new(py, &blob)))
    }

    fn put(&self, key: &str, blob: &[u8]) -> PyResult<bool> {
        if nuxiva_stage_core::decode(blob).is_err() {
            return Ok(false);
        }
        let mut guard = self.inner.lock().map_err(|_| poisoned())?;
        Ok(guard.put(key, blob.to_vec()))
    }

    fn __len__(&self) -> PyResult<usize> {
        let guard = self.inner.lock().map_err(|_| poisoned())?;
        Ok(guard.len())
    }
}
