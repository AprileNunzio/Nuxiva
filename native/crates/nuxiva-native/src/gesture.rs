use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use std::sync::Mutex;

fn invalid(error: &nuxiva_gesture_core::GestureError) -> PyErr {
    PyValueError::new_err(error.to_string())
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustGestureEngine {
    inner: Mutex<nuxiva_gesture_core::GestureEngine>,
}

#[pymethods]
impl RustGestureEngine {
    #[new]
    #[pyo3(signature = (profile_json = ""))]
    fn new(profile_json: &str) -> PyResult<Self> {
        let profile = nuxiva_gesture_core::GestureProfile::from_json(profile_json)
            .map_err(|e| invalid(&e))?;
        Ok(Self {
            inner: Mutex::new(nuxiva_gesture_core::GestureEngine::new(profile)),
        })
    }

    fn feed_json(&self, frame_json: &str, context: &str) -> PyResult<String> {
        let frame =
            nuxiva_gesture_core::wire::frame_from_json(frame_json).map_err(|e| invalid(&e))?;
        let events = {
            let mut engine = self
                .inner
                .lock()
                .map_err(|_| PyRuntimeError::new_err("state is poisoned"))?;
            engine.feed(&frame, context)
        };
        nuxiva_gesture_core::wire::events_to_json(&events).map_err(|e| invalid(&e))
    }

    fn set_profile(&self, profile_json: &str) -> PyResult<()> {
        let profile = nuxiva_gesture_core::GestureProfile::from_json(profile_json)
            .map_err(|e| invalid(&e))?;
        let mut engine = self
            .inner
            .lock()
            .map_err(|_| PyRuntimeError::new_err("state is poisoned"))?;
        engine.set_profile(profile);
        Ok(())
    }

    fn profile_json(&self) -> PyResult<String> {
        let engine = self
            .inner
            .lock()
            .map_err(|_| PyRuntimeError::new_err("state is poisoned"))?;
        engine.profile().to_json().map_err(|e| invalid(&e))
    }
}

#[pyfunction]
pub fn gesture_validate_profile(profile_json: &str) -> PyResult<String> {
    nuxiva_gesture_core::GestureProfile::from_json(profile_json)
        .and_then(|p| p.to_json())
        .map_err(|e| invalid(&e))
}

#[pyfunction]
pub fn gesture_catalog() -> Vec<String> {
    nuxiva_gesture_core::GestureKind::catalog()
        .into_iter()
        .map(nuxiva_gesture_core::GestureKind::id)
        .collect()
}
