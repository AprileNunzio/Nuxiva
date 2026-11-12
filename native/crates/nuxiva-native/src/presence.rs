use crate::errors::poisoned;
use nuxiva_presence_core::{Policy, Signals, Tracker};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use std::sync::Mutex;

const MAX_SIGNALS: usize = 256 * 1024;

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustPresenceTracker {
    inner: Mutex<Tracker>,
}

#[pymethods]
impl RustPresenceTracker {
    #[new]
    fn new(policy_json: &str, now_ms: u64) -> PyResult<Self> {
        let policy: Policy =
            serde_json::from_str(policy_json).map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok(Self {
            inner: Mutex::new(Tracker::new(policy, now_ms)),
        })
    }

    fn step(&self, signals_json: &str, now_ms: u64) -> PyResult<String> {
        if signals_json.len() > MAX_SIGNALS {
            return Err(PyValueError::new_err("presence signals too large"));
        }
        let signals: Signals =
            serde_json::from_str(signals_json).map_err(|e| PyValueError::new_err(e.to_string()))?;
        let audience = self
            .inner
            .lock()
            .map_err(|_| poisoned())?
            .step(&signals, now_ms);
        serde_json::to_string(&audience).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }
}
