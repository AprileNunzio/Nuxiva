use std::sync::Mutex;

use nuxiva_guard_core::{
    GuardError, LoginLimiter, OriginRequest, RedirectRequest, SessionCodec, decode_value, entries,
    format_line, host_allowed, normalize, normalize_name, redirect_target, safe_host, verdict,
};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

use crate::errors::poisoned;

const MAX_INPUT: usize = 1 << 20;

fn guard_error(error: GuardError) -> PyErr {
    PyValueError::new_err(error.code())
}

fn bounded(text: &str) -> PyResult<&str> {
    if text.len() > MAX_INPUT {
        return Err(PyValueError::new_err("guard.input.too_large"));
    }
    Ok(text)
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustSessionCodec {
    inner: SessionCodec,
}

#[pymethods]
impl RustSessionCodec {
    #[new]
    fn new(secret: &[u8]) -> PyResult<Self> {
        Ok(Self {
            inner: SessionCodec::new(secret).map_err(guard_error)?,
        })
    }

    fn issue(&self, username: &str, now: i64, ttl: i64) -> PyResult<String> {
        self.inner.issue(username, now, ttl).map_err(guard_error)
    }

    #[pyo3(signature = (token, now))]
    fn verify(&self, token: Option<&str>, now: f64) -> Option<String> {
        token.and_then(|t| self.inner.verify(t, now))
    }
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug, Default)]
pub struct RustLoginLimiter {
    inner: Mutex<LoginLimiter>,
}

#[pymethods]
impl RustLoginLimiter {
    #[new]
    fn new() -> Self {
        Self::default()
    }

    fn limited(&self, ip: &str, now: f64) -> PyResult<bool> {
        let mut inner = self.inner.lock().map_err(|_| poisoned())?;
        Ok(inner.limited(ip, now))
    }

    fn fail(&self, ip: &str, now: f64) -> PyResult<()> {
        let mut inner = self.inner.lock().map_err(|_| poisoned())?;
        inner.fail(ip, now);
        Ok(())
    }

    fn tracked(&self) -> PyResult<usize> {
        let inner = self.inner.lock().map_err(|_| poisoned())?;
        Ok(inner.tracked())
    }
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustOriginGuard {
    trusted: Vec<String>,
}

#[pymethods]
impl RustOriginGuard {
    #[new]
    fn new(trusted: Vec<String>) -> Self {
        let mut trusted: Vec<String> = trusted.into_iter().map(|h| h.to_lowercase()).collect();
        trusted.sort_unstable();
        trusted.dedup();
        Self { trusted }
    }

    fn host_allowed(&self, host: &str) -> bool {
        host_allowed(host, &self.trusted)
    }

    fn verdict(&self, host: &str, method: &str, fetch_site: &str, origin: &str) -> &'static str {
        verdict(
            OriginRequest {
                host,
                method,
                fetch_site,
                origin,
            },
            &self.trusted,
        )
        .code()
    }
}

#[pyfunction]
pub fn guard_safe_host(authority: &str) -> String {
    safe_host(authority)
}

#[pyfunction]
#[allow(clippy::too_many_arguments)]
#[pyo3(signature = (scheme, client, path, method, fetch_mode, accept, host, query, admin, port))]
pub fn guard_redirect_target(
    scheme: &str,
    client: &str,
    path: &str,
    method: &str,
    fetch_mode: &str,
    accept: &str,
    host: &str,
    query: &[u8],
    admin: bool,
    port: i64,
) -> String {
    let request = RedirectRequest {
        scheme,
        client,
        path,
        method,
        fetch_mode,
        accept,
        host,
        query,
    };
    redirect_target(&request, admin, port)
}

#[pyfunction]
pub fn env_decode_value(value: &str) -> PyResult<String> {
    Ok(decode_value(bounded(value)?))
}

#[pyfunction]
pub fn env_format_line(key: &str, value: &str) -> PyResult<String> {
    format_line(key, bounded(value)?).map_err(guard_error)
}

#[pyfunction]
pub fn env_entries(text: &str) -> PyResult<Vec<(Option<String>, String)>> {
    Ok(entries(bounded(text)?))
}

#[pyfunction]
pub fn env_normalize(text: &str) -> PyResult<String> {
    normalize(bounded(text)?).map_err(guard_error)
}

#[pyfunction]
pub fn identity_normalize_name(raw: &str) -> PyResult<String> {
    Ok(normalize_name(bounded(raw)?))
}
