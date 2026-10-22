use crate::errors::poisoned;
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use std::sync::{Arc, RwLock};

#[pyclass(module = "nuxiva_native")]
#[derive(Debug, Clone)]
pub struct RustSpatialArbiter {
    inner: nuxiva_spatial_core::PriorityArbiter,
    deferred_queue: Arc<RwLock<nuxiva_spatial_core::DeferredQueue>>,
}

#[pymethods]
impl RustSpatialArbiter {
    #[new]
    fn new() -> Self {
        Self {
            inner: nuxiva_spatial_core::PriorityArbiter::new(),
            deferred_queue: Arc::new(RwLock::new(nuxiva_spatial_core::DeferredQueue::new())),
        }
    }

    fn arbitrate_json(&self, event_json: &str, manifest_json: &str) -> PyResult<String> {
        let event: nuxiva_spatial_core::NotificationEvent =
            serde_json::from_str(event_json).map_err(|e| PyValueError::new_err(e.to_string()))?;
        let manifest: nuxiva_spatial_core::ContextManifest = serde_json::from_str(manifest_json)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        let res = self.inner.arbitrate(&event, &manifest);
        if res.should_defer {
            let mut guard = self.deferred_queue.write().map_err(|_| poisoned())?;
            guard.push(event);
        }
        serde_json::to_string(&res).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    fn drain_deferred_json(&self) -> PyResult<String> {
        let mut guard = self.deferred_queue.write().map_err(|_| poisoned())?;
        let items = guard.drain_all();
        serde_json::to_string(&items).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    fn deferred_count(&self) -> PyResult<usize> {
        let guard = self.deferred_queue.read().map_err(|_| poisoned())?;
        Ok(guard.len())
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug, Default)]
pub struct RustIntentRouter {
    inner: nuxiva_spatial_core::IntentRouter,
}

#[pymethods]
impl RustIntentRouter {
    #[new]
    fn new() -> Self {
        Self {
            inner: nuxiva_spatial_core::IntentRouter::new(),
        }
    }

    fn resolve_intent(&self, raw_utterance: &str) -> Option<String> {
        self.inner.resolve_intent(raw_utterance).map(str::to_owned)
    }
}
