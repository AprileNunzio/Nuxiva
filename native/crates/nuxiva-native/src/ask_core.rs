use nuxiva_ask_core::{AskQuery, ask, evaluate, parse};
use nuxiva_memory_core::Sighting;
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;

const MAX_INPUT_JSON: usize = 1024 * 1024;

fn bad_arg<E: std::fmt::Display>(e: E) -> PyErr {
    PyValueError::new_err(e.to_string())
}

fn err_rt<E: std::fmt::Display>(e: E) -> PyErr {
    PyRuntimeError::new_err(e.to_string())
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug, Default)]
pub struct RustAskCore;

#[pymethods]
#[allow(clippy::unused_self)]
impl RustAskCore {
    #[new]
    pub fn new() -> Self {
        Self
    }

    pub fn parse(&self, text: &str, now_ms: u64) -> PyResult<String> {
        let query = parse(text, now_ms).map_err(bad_arg)?;
        serde_json::to_string(&query).map_err(err_rt)
    }

    pub fn evaluate(&self, query_json: &str, sightings_json: &str) -> PyResult<String> {
        if query_json.len() > MAX_INPUT_JSON || sightings_json.len() > MAX_INPUT_JSON {
            return Err(PyValueError::new_err("input json too large"));
        }
        let query: AskQuery = serde_json::from_str(query_json).map_err(bad_arg)?;
        let sightings: Vec<Sighting> = serde_json::from_str(sightings_json).map_err(bad_arg)?;
        let answer = evaluate(&query, &sightings);
        serde_json::to_string(&answer).map_err(err_rt)
    }

    pub fn ask(&self, text: &str, now_ms: u64, sightings_json: &str) -> PyResult<String> {
        if sightings_json.len() > MAX_INPUT_JSON {
            return Err(PyValueError::new_err("input json too large"));
        }
        let sightings: Vec<Sighting> = serde_json::from_str(sightings_json).map_err(bad_arg)?;
        let answer = ask(text, now_ms, &sightings).map_err(bad_arg)?;
        serde_json::to_string(&answer).map_err(err_rt)
    }
}
