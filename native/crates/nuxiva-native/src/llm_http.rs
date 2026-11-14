use std::sync::OnceLock;
use std::time::Duration;

use nuxiva_llm_client::{ClientError, LlmClient};
use pyo3::exceptions::{PyOSError, PyValueError};
use pyo3::prelude::*;
use tokio::runtime::{Builder, Runtime};

const MAX_REQUEST: usize = 4 << 20;
const MAX_TIMEOUT: f64 = 3600.0;
const CONNECT_SECONDS: u64 = 10;

fn runtime() -> PyResult<&'static Runtime> {
    static RUNTIME: OnceLock<Result<Runtime, String>> = OnceLock::new();
    RUNTIME
        .get_or_init(|| {
            Builder::new_multi_thread()
                .worker_threads(2)
                .enable_all()
                .build()
                .map_err(|error| error.to_string())
        })
        .as_ref()
        .map_err(|error| PyOSError::new_err(error.clone()))
}

fn failure(error: &ClientError) -> PyErr {
    match error {
        ClientError::Url | ClientError::Json | ClientError::Build => {
            PyValueError::new_err(error.to_string())
        }
        ClientError::Transport | ClientError::Timeout | ClientError::TooLarge => {
            PyOSError::new_err(error.to_string())
        }
    }
}

#[pyfunction]
#[pyo3(signature = (base_url, path, body, timeout, bearer=None))]
#[allow(clippy::needless_pass_by_value)]
fn llm_post_json(
    py: Python<'_>,
    base_url: &str,
    path: &str,
    body: &str,
    timeout: f64,
    bearer: Option<String>,
) -> PyResult<(u16, String)> {
    if body.len() > MAX_REQUEST || !timeout.is_finite() || timeout <= 0.0 || timeout > MAX_TIMEOUT {
        return Err(PyValueError::new_err("llm.client.request_invalid"));
    }
    let value: serde_json::Value =
        serde_json::from_str(body).map_err(|_| PyValueError::new_err("llm.client.json_invalid"))?;
    let client = LlmClient::new(
        base_url,
        Duration::from_secs_f64(timeout),
        Duration::from_secs(CONNECT_SECONDS),
    )
    .map_err(|error| failure(&error))?;
    let runtime = runtime()?;
    let reply = py
        .detach(|| runtime.block_on(client.post_json(path, &value, bearer.as_deref())))
        .map_err(|error| failure(&error))?;
    Ok((reply.status, reply.body))
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(llm_post_json, m)?)
}
