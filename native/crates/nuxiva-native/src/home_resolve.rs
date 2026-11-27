use home_resolve::{Request, Resolver};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

const MAX_REQUEST_BYTES: usize = 4 * 1024;

fn invalid(error: impl std::fmt::Display) -> PyErr {
    PyValueError::new_err(error.to_string())
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustHomeResolver {
    inner: Resolver,
}

#[pymethods]
impl RustHomeResolver {
    #[new]
    fn new(inventory_json: &str) -> PyResult<Self> {
        Ok(Self {
            inner: Resolver::from_json(inventory_json).map_err(invalid)?,
        })
    }

    fn resolve(&self, py: Python<'_>, request_json: &str) -> PyResult<String> {
        if request_json.len() > MAX_REQUEST_BYTES {
            return Err(PyValueError::new_err("home.resolve.too_large.request"));
        }
        let request: Request = serde_json::from_str(request_json).map_err(invalid)?;
        let resolution = py
            .detach(|| self.inner.resolve(&request))
            .map_err(invalid)?;
        serde_json::to_string(&resolution).map_err(invalid)
    }

    fn relevance(&self, py: Python<'_>, request_json: &str) -> PyResult<String> {
        if request_json.len() > MAX_REQUEST_BYTES {
            return Err(PyValueError::new_err("home.resolve.too_large.request"));
        }
        let request: Request = serde_json::from_str(request_json).map_err(invalid)?;
        let relevance = py
            .detach(|| self.inner.relevance(&request))
            .map_err(invalid)?;
        serde_json::to_string(&relevance).map_err(invalid)
    }

    #[staticmethod]
    fn thresholds() -> (f64, f64) {
        (home_resolve::EXECUTE, home_resolve::CONFIRM)
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustHomeResolver>()?;
    Ok(())
}
