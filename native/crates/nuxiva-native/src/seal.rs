use nuxiva_seal_core::{Fernet, SealError, generate_key};
use pyo3::create_exception;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;

create_exception!(nuxiva_native, SealRejected, PyValueError);

fn rejected(error: SealError) -> PyErr {
    SealRejected::new_err(error.code())
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustFernet {
    inner: Fernet,
}

#[pymethods]
impl RustFernet {
    #[new]
    fn new(key: &[u8]) -> PyResult<Self> {
        Ok(Self {
            inner: Fernet::new(key).map_err(rejected)?,
        })
    }

    #[staticmethod]
    fn generate_key(py: Python<'_>) -> PyResult<Bound<'_, PyBytes>> {
        let key = generate_key().map_err(rejected)?;
        Ok(PyBytes::new(py, key.as_bytes()))
    }

    fn encrypt<'py>(
        &self,
        py: Python<'py>,
        data: &[u8],
        now: i64,
    ) -> PyResult<Bound<'py, PyBytes>> {
        let owned = data.to_vec();
        let token = py
            .detach(|| self.inner.encrypt(&owned, now))
            .map_err(rejected)?;
        Ok(PyBytes::new(py, token.as_bytes()))
    }

    #[pyo3(signature = (token, now, ttl = None))]
    fn decrypt<'py>(
        &self,
        py: Python<'py>,
        token: &[u8],
        now: i64,
        ttl: Option<i64>,
    ) -> PyResult<Bound<'py, PyBytes>> {
        let owned = token.to_vec();
        let plain = py
            .detach(|| self.inner.decrypt(&owned, ttl, now))
            .map_err(rejected)?;
        Ok(PyBytes::new(py, &plain))
    }
}
