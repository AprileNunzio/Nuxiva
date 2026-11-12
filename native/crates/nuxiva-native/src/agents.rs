use crate::errors::poisoned;
use nuxiva_agent_core::{Registry, Root};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use std::sync::Mutex;

const MAX_ROOTS: usize = 16;
const MAX_QUERY: usize = 4_096;

fn json<T: serde::Serialize>(value: &T) -> PyResult<String> {
    serde_json::to_string(value).map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

#[pyfunction]
#[pyo3(signature = (raw, folder, category=None))]
pub fn agent_manifest_validate(
    raw: &str,
    folder: &str,
    category: Option<&str>,
) -> PyResult<String> {
    json(&nuxiva_agent_core::validate(raw, folder, category))
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustAgentRegistry {
    inner: Mutex<Registry>,
}

#[pymethods]
impl RustAgentRegistry {
    #[new]
    fn new() -> Self {
        Self {
            inner: Mutex::new(Registry::new()),
        }
    }

    fn refresh(&self, py: Python<'_>, roots_json: &str) -> PyResult<bool> {
        let roots: Vec<Root> =
            serde_json::from_str(roots_json).map_err(|e| PyValueError::new_err(e.to_string()))?;
        if roots.len() > MAX_ROOTS {
            return Err(PyValueError::new_err("too many agent roots"));
        }
        py.detach(|| {
            let mut guard = self.inner.lock().map_err(|_| poisoned())?;
            Ok(guard.refresh(&roots))
        })
    }

    fn snapshot(&self) -> PyResult<String> {
        let guard = self.inner.lock().map_err(|_| poisoned())?;
        json(guard.snapshot())
    }

    fn signature(&self) -> PyResult<String> {
        let guard = self.inner.lock().map_err(|_| poisoned())?;
        Ok(guard.snapshot().signature.clone())
    }

    fn search(&self, query: &str, limit: usize) -> PyResult<Vec<(String, usize)>> {
        if query.len() > MAX_QUERY {
            return Err(PyValueError::new_err("query too long"));
        }
        let guard = self.inner.lock().map_err(|_| poisoned())?;
        Ok(guard.snapshot().search(query, limit.min(256)))
    }
}
