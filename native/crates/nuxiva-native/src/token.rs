use nuxiva_token_core::{MAX_CLAIMS, TokenCodec, TokenError};
use pyo3::create_exception;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use serde_json::{Map, Value};

create_exception!(nuxiva_native, TokenRejected, PyValueError);

fn rejected(error: TokenError) -> PyErr {
    TokenRejected::new_err(error.code())
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustTokenCodec {
    inner: TokenCodec,
}

#[pymethods]
impl RustTokenCodec {
    #[new]
    fn new(secret: &[u8]) -> PyResult<Self> {
        Ok(Self {
            inner: TokenCodec::new(secret).map_err(rejected)?,
        })
    }

    fn issue(&self, subject: &str, claims_json: &str, now: i64, ttl: i64) -> PyResult<String> {
        if claims_json.len() > MAX_CLAIMS {
            return Err(rejected(TokenError::Claims));
        }
        let claims: Map<String, Value> =
            serde_json::from_str(claims_json).map_err(|_| rejected(TokenError::Claims))?;
        self.inner
            .issue(subject, claims, now, ttl)
            .map_err(rejected)
    }

    fn verify(&self, py: Python<'_>, token: &str, now: i64) -> PyResult<String> {
        let payload = py
            .detach(|| self.inner.verify(token, now))
            .map_err(rejected)?;
        serde_json::to_string(&payload).map_err(|_| rejected(TokenError::Payload))
    }
}
