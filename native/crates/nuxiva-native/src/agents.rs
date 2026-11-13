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

#[pyfunction]
pub fn agent_layout_inspect(dir: &str) -> PyResult<String> {
    json(&nuxiva_agent_core::inspect(std::path::Path::new(dir)))
}

#[pyfunction]
pub fn widget_inspect(dir: &str) -> PyResult<String> {
    json(&nuxiva_agent_core::widget::inspect(std::path::Path::new(
        dir,
    )))
}

#[pyfunction]
pub fn agent_scaffold(spec_json: &str) -> PyResult<Vec<(String, Vec<u8>)>> {
    if spec_json.len() > 64 * 1024 {
        return Err(PyValueError::new_err("scaffold spec too large"));
    }
    let spec: nuxiva_agent_core::ScaffoldSpec =
        serde_json::from_str(spec_json).map_err(|e| PyValueError::new_err(e.to_string()))?;
    match nuxiva_agent_core::scaffold(&spec) {
        Ok(files) => Ok(files.into_iter().map(|f| (f.path, f.bytes)).collect()),
        Err(issues) => Err(PyValueError::new_err(json(&issues)?)),
    }
}

#[pyfunction]
pub fn agent_icon(category: &str, id: &str) -> PyResult<Vec<u8>> {
    if category.len() > 64 || id.len() > 64 {
        return Err(PyValueError::new_err("icon input too long"));
    }
    Ok(nuxiva_agent_core::icon::render(category, id))
}

#[pyfunction]
pub fn agent_genesis_decide(case_json: &str) -> PyResult<String> {
    if case_json.len() > 64 * 1024 {
        return Err(PyValueError::new_err("genesis case too large"));
    }
    let case: nuxiva_agent_core::genesis::Case =
        serde_json::from_str(case_json).map_err(|e| PyValueError::new_err(e.to_string()))?;
    json(&nuxiva_agent_core::genesis::decide(&case))
}
