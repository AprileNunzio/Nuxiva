use std::net::{IpAddr, ToSocketAddrs};
use std::time::{Duration, Instant};

use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use serde_json::{Value, json};

const MAX_REPLY: u64 = 2 * 1024 * 1024;
const MAX_KEY: usize = 512;
const MAX_TIMEOUT_SECONDS: u64 = 300;
const MAX_FAILURE_MESSAGE: usize = 240;
const BLOCKED_HOSTS: [&str; 2] = ["metadata.google.internal", "metadata"];

fn failed(error: impl std::fmt::Display) -> PyErr {
    PyValueError::new_err(error.to_string())
}

fn forbidden(ip: IpAddr) -> bool {
    match ip {
        IpAddr::V4(v4) => {
            v4.is_link_local() || v4.is_unspecified() || v4.is_multicast() || v4.is_broadcast()
        }
        IpAddr::V6(v6) => {
            v6.is_unspecified()
                || v6.is_multicast()
                || (v6.segments().first().is_some_and(|s| s & 0xffc0 == 0xfe80))
        }
    }
}

fn checked_base(base: &str) -> PyResult<ureq::http::Uri> {
    if base.len() > 256 || base.chars().any(char::is_control) {
        return Err(PyValueError::new_err("endpoint_invalid"));
    }
    let uri: ureq::http::Uri = base
        .parse()
        .map_err(|_| PyValueError::new_err("endpoint_invalid"))?;
    let scheme_ok = matches!(uri.scheme_str(), Some("http" | "https"));
    let authority = uri
        .authority()
        .ok_or_else(|| PyValueError::new_err("endpoint_invalid"))?;
    if !scheme_ok || authority.as_str().contains('@') || uri.query().is_some() {
        return Err(PyValueError::new_err("endpoint_invalid"));
    }
    let host = authority
        .host()
        .trim_matches(['[', ']'])
        .to_ascii_lowercase();
    if BLOCKED_HOSTS.contains(&host.as_str()) {
        return Err(PyValueError::new_err("endpoint_forbidden"));
    }
    let port = authority
        .port_u16()
        .unwrap_or(if uri.scheme_str() == Some("https") {
            443
        } else {
            80
        });
    let addresses: Vec<_> = (host.as_str(), port)
        .to_socket_addrs()
        .map_err(|_| PyValueError::new_err("endpoint_unreachable"))?
        .collect();
    if addresses.is_empty() || addresses.iter().any(|a| forbidden(a.ip())) {
        return Err(PyValueError::new_err("endpoint_forbidden"));
    }
    Ok(uri)
}

fn failure_message(body: Option<&str>) -> String {
    let body = body.unwrap_or_default();
    let parsed: Option<Value> = serde_json::from_str(body).ok();
    let message = parsed
        .as_ref()
        .and_then(|v| {
            v.pointer("/error/message")
                .or_else(|| v.get("error"))
                .or_else(|| v.get("message"))
        })
        .and_then(Value::as_str)
        .unwrap_or(body);
    message
        .chars()
        .filter(|c| !c.is_control())
        .take(MAX_FAILURE_MESSAGE)
        .collect()
}

#[pyfunction]
fn reason_lab_inspect(dataset: &str) -> PyResult<String> {
    reason_lab::facade::inspect_dataset(dataset.as_bytes()).map_err(failed)
}

#[pyfunction]
fn reason_lab_cases(dataset: &str) -> PyResult<String> {
    reason_lab::facade::list_cases(dataset.as_bytes()).map_err(failed)
}

#[pyfunction]
fn reason_lab_report(dataset: &str, outcomes: &str) -> PyResult<String> {
    reason_lab::facade::report(dataset.as_bytes(), outcomes.as_bytes()).map_err(failed)
}

#[pyfunction]
fn reason_lab_rows(dataset: &str, outcomes: &str) -> PyResult<String> {
    reason_lab::facade::rows(dataset.as_bytes(), outcomes.as_bytes()).map_err(failed)
}

#[pyfunction]
fn reason_lab_compare(baseline: &str, candidate: &str) -> PyResult<String> {
    reason_lab::facade::compare(baseline.as_bytes(), candidate.as_bytes()).map_err(failed)
}

#[pyfunction]
fn reason_lab_check_endpoint(py: Python<'_>, base: String) -> PyResult<()> {
    py.detach(move || checked_base(&base).map(|_| ()))
}

#[pyfunction]
#[pyo3(signature = (backend, base, model, key, case_id, text, external, timeout_seconds))]
#[allow(clippy::too_many_arguments)]
fn reason_lab_run_case(
    py: Python<'_>,
    backend: String,
    base: String,
    model: String,
    key: Option<String>,
    case_id: String,
    text: String,
    external: Option<String>,
    timeout_seconds: u64,
) -> PyResult<String> {
    if key.as_ref().is_some_and(|k| k.len() > MAX_KEY) {
        return Err(PyValueError::new_err("key_invalid"));
    }
    let timeout = Duration::from_secs(timeout_seconds.clamp(1, MAX_TIMEOUT_SECONDS));
    py.detach(move || {
        checked_base(&base)?;
        let prepared: Value = serde_json::from_str(
            &reason_lab::facade::request(&backend, &base, &model, &text, external.as_deref())
                .map_err(failed)?,
        )
        .map_err(failed)?;
        let url = prepared
            .get("url")
            .and_then(Value::as_str)
            .unwrap_or_default()
            .to_owned();
        checked_base(&url)?;
        let payload = prepared.get("body").cloned().unwrap_or(Value::Null);
        let agent: ureq::Agent = ureq::Agent::config_builder()
            .max_redirects(0)
            .http_status_as_error(false)
            .timeout_global(Some(timeout))
            .build()
            .into();
        let mut request = agent.post(&url);
        if let Some(token) = key.as_deref().filter(|k| !k.is_empty()) {
            request = request.header("Authorization", format!("Bearer {token}"));
        }
        let started = Instant::now();
        let answer = request.send_json(&payload);
        let latency = u64::try_from(started.elapsed().as_millis()).unwrap_or(u64::MAX);
        let (status, body) = match answer {
            Ok(mut response) => {
                let status = response.status().as_u16();
                let body = response
                    .body_mut()
                    .with_config()
                    .limit(MAX_REPLY)
                    .read_to_string()
                    .ok();
                (status, body)
            }
            Err(_) => (0, None),
        };
        let usable = if status == 200 { body.as_deref() } else { None };
        let outcome = reason_lab::facade::outcome(&backend, &case_id, &text, usable, latency)
            .map_err(failed)?;
        let outcome: Value =
            serde_json::from_str(&outcome).map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
        let failure = (status != 200).then(
            || json!({"status": status, "url": url, "message": failure_message(body.as_deref())}),
        );
        serde_json::to_string(&json!({"status": status, "outcome": outcome, "failure": failure}))
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))
    })
}

pub(crate) fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(reason_lab_inspect, module)?)?;
    module.add_function(wrap_pyfunction!(reason_lab_cases, module)?)?;
    module.add_function(wrap_pyfunction!(reason_lab_report, module)?)?;
    module.add_function(wrap_pyfunction!(reason_lab_rows, module)?)?;
    module.add_function(wrap_pyfunction!(reason_lab_compare, module)?)?;
    module.add_function(wrap_pyfunction!(reason_lab_check_endpoint, module)?)?;
    module.add_function(wrap_pyfunction!(reason_lab_run_case, module)?)
}

#[cfg(test)]
#[allow(clippy::expect_used, clippy::panic)]
mod tests {
    use super::{checked_base, failure_message};

    #[test]
    fn local_and_lan_endpoints_are_allowed() {
        assert!(checked_base("http://127.0.0.1:11434").is_ok());
        assert!(checked_base("http://localhost:11434").is_ok());
        assert!(checked_base("http://10.0.0.5:11434").is_ok());
    }

    #[test]
    fn failure_messages_come_from_the_provider_error() {
        let groq =
            r#"{"error":{"message":"The model `x` does not exist","code":"model_not_found"}}"#;
        assert_eq!(failure_message(Some(groq)), "The model `x` does not exist");
        assert_eq!(failure_message(Some("not found\n")), "not found");
        assert_eq!(failure_message(None), "");
    }

    #[test]
    fn metadata_and_malformed_endpoints_are_refused() {
        for base in [
            "http://169.254.169.254/latest",
            "http://metadata.google.internal",
            "http://[fe80::1]:80",
            "http://0.0.0.0:80",
            "ftp://127.0.0.1",
            "http://user:pw@127.0.0.1",
            "http://127.0.0.1/?a=b",
            "not a url",
            "",
        ] {
            assert!(checked_base(base).is_err(), "{base}");
        }
    }
}
