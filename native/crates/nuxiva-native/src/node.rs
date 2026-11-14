use nuxiva_node_core::announce::{self, Hardware};
use nuxiva_node_core::audit::{self, Entry};
use nuxiva_node_core::authorize::{Verdict, authorize, effective};
use nuxiva_node_core::identity;
use nuxiva_node_core::profile::{Ceiling, Mode, Profile, resolve};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::wrap_pyfunction;
use serde_json::json;

const MAX_ENTRIES: usize = 8192;
const MAX_LIST: usize = 128;

fn reject(error: nuxiva_node_core::NodeError) -> PyErr {
    PyValueError::new_err(error.code())
}

fn mode_of(raw: &str) -> Mode {
    if raw == "second_server" {
        Mode::SecondServer
    } else {
        Mode::Satellite
    }
}

#[pyfunction]
fn node_resolve_mode(
    profile: &str,
    cpu_cores: u32,
    ram_mb: u64,
    full_host: bool,
    second_server_allowed: bool,
) -> String {
    let hardware = Hardware { cpu_cores, ram_mb };
    let ceiling = Ceiling {
        second_server: second_server_allowed,
    };
    resolve(Profile::parse(profile), &hardware, full_host, ceiling)
        .as_str()
        .to_owned()
}

#[pyfunction]
fn node_parse_announce(raw: &str) -> PyResult<String> {
    let parsed = announce::parse(raw).map_err(reject)?;
    Ok(json!({
        "scopes": parsed.scopes,
        "rejected": parsed.rejected,
        "cpu_cores": parsed.hardware.cpu_cores,
        "ram_mb": parsed.hardware.ram_mb,
        "full_host": parsed.full_host,
    })
    .to_string())
}

#[pyfunction]
#[allow(clippy::needless_pass_by_value)]
fn node_effective_scopes(
    mode: &str,
    announced: Vec<String>,
    grants: Vec<String>,
) -> PyResult<Vec<String>> {
    if announced.len() > MAX_LIST || grants.len() > MAX_LIST {
        return Err(PyValueError::new_err("node.error.too_many"));
    }
    Ok(effective(mode_of(mode), &announced, &grants))
}

#[pyfunction]
#[allow(clippy::needless_pass_by_value)]
fn node_authorize(effective_scopes: Vec<String>, requested: &str) -> PyResult<(bool, String)> {
    if effective_scopes.len() > MAX_LIST {
        return Err(PyValueError::new_err("node.error.too_many"));
    }
    Ok(match authorize(&effective_scopes, requested) {
        Verdict::Allow => (true, String::new()),
        Verdict::Deny(code) => (false, code.to_owned()),
    })
}

#[pyfunction]
#[allow(clippy::too_many_arguments)]
fn node_verify_request(
    key_hex: &str,
    signature_hex: &str,
    node: &str,
    method: &str,
    path: &str,
    ts: i64,
    nonce: &str,
    body_sha256: &str,
    now: i64,
) -> PyResult<()> {
    identity::verify_request(
        key_hex,
        signature_hex,
        node,
        method,
        path,
        ts,
        nonce,
        body_sha256,
        now,
    )
    .map_err(reject)
}

#[pyfunction]
fn node_fingerprint(key_hex: &str) -> PyResult<String> {
    identity::fingerprint(key_hex).map_err(reject)
}

#[pyfunction]
fn node_pairing_code(key_hex: &str) -> PyResult<String> {
    identity::pairing_code(key_hex).map_err(reject)
}

#[pyfunction]
#[allow(clippy::too_many_arguments)]
fn node_audit_seal(
    prev: &str,
    seq: u64,
    ts: i64,
    actor: &str,
    node: &str,
    action: &str,
    detail: &str,
) -> PyResult<String> {
    serde_json::to_string(&audit::seal(prev, seq, ts, actor, node, action, detail))
        .map_err(|_| PyValueError::new_err("node.error.payload"))
}

#[pyfunction]
fn node_audit_verify(anchor: &str, entries_json: &str) -> PyResult<i64> {
    let entries: Vec<Entry> = serde_json::from_str(entries_json)
        .map_err(|_| PyValueError::new_err("node.error.payload"))?;
    if entries.len() > MAX_ENTRIES {
        return Err(PyValueError::new_err("node.error.too_many"));
    }
    Ok(audit::verify_chain(anchor, &entries)
        .map_or(-1, |index| i64::try_from(index).unwrap_or(i64::MAX)))
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(node_resolve_mode, m)?)?;
    m.add_function(wrap_pyfunction!(node_parse_announce, m)?)?;
    m.add_function(wrap_pyfunction!(node_effective_scopes, m)?)?;
    m.add_function(wrap_pyfunction!(node_authorize, m)?)?;
    m.add_function(wrap_pyfunction!(node_verify_request, m)?)?;
    m.add_function(wrap_pyfunction!(node_fingerprint, m)?)?;
    m.add_function(wrap_pyfunction!(node_pairing_code, m)?)?;
    m.add_function(wrap_pyfunction!(node_audit_seal, m)?)?;
    m.add_function(wrap_pyfunction!(node_audit_verify, m)?)?;
    Ok(())
}
