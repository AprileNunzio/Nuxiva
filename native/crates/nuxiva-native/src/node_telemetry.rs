use nuxiva_node_core::proximity;
use nuxiva_node_core::telemetry;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::wrap_pyfunction;
use serde_json::Value;

const MAX_PAYLOAD: usize = 1 << 20;

fn parse(raw: &str) -> PyResult<Value> {
    if raw.len() > MAX_PAYLOAD {
        return Err(PyValueError::new_err("node.error.too_many"));
    }
    serde_json::from_str(raw).map_err(|_| PyValueError::new_err("node.error.payload"))
}

fn dump(value: &impl serde::Serialize) -> PyResult<String> {
    serde_json::to_string(value).map_err(|_| PyValueError::new_err("node.error.payload"))
}

#[pyfunction]
fn node_clean_metrics(raw: &str) -> PyResult<String> {
    dump(&telemetry::clean_metrics(&parse(raw)?))
}

#[pyfunction]
fn node_clean_proximity(raw: &str, now: f64) -> PyResult<String> {
    dump(&telemetry::clean_proximity(&parse(raw)?, now))
}

#[pyfunction]
fn node_nearest(nodes: &str, now: f64) -> PyResult<String> {
    dump(&proximity::nearest(&parse(nodes)?, now))
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(node_clean_metrics, m)?)?;
    m.add_function(wrap_pyfunction!(node_clean_proximity, m)?)?;
    m.add_function(wrap_pyfunction!(node_nearest, m)?)?;
    Ok(())
}
