use crate::errors::poisoned;
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use std::sync::{Arc, RwLock};

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustFastMemory {
    inner: Arc<RwLock<nuxiva_spatial_core::FastSemanticMemory>>,
}

#[pymethods]
impl RustFastMemory {
    #[new]
    #[pyo3(signature = (max_capacity = 512))]
    fn new(max_capacity: usize) -> Self {
        Self {
            inner: Arc::new(RwLock::new(nuxiva_spatial_core::FastSemanticMemory::new(
                max_capacity,
            ))),
        }
    }

    fn insert(
        &self,
        key: &str,
        embedding: Vec<f32>,
        response_key: &str,
        payload_json: &str,
        timestamp_ms: u64,
    ) -> PyResult<()> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        guard.insert(nuxiva_spatial_core::MemoryEntry::new(
            key,
            embedding,
            response_key,
            payload_json,
            timestamp_ms,
        ));
        Ok(())
    }

    #[allow(clippy::needless_pass_by_value)]
    fn lookup_json(
        &self,
        exact_key: &str,
        query_embedding: Vec<f32>,
        similarity_threshold: f32,
    ) -> PyResult<Option<String>> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        let hit = guard.lookup(exact_key, &query_embedding, similarity_threshold);
        match hit {
            Some(h) => {
                let json = serde_json::to_string(&h)
                    .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
                Ok(Some(json))
            }
            None => Ok(None),
        }
    }

    fn prune_lru(&self, target_size: usize) -> PyResult<()> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        guard.prune_lru(target_size);
        Ok(())
    }

    fn clear(&self) -> PyResult<()> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        guard.clear();
        Ok(())
    }

    fn len(&self) -> PyResult<usize> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        Ok(guard.len())
    }

    fn is_empty(&self) -> PyResult<bool> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        Ok(guard.is_empty())
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug, Default)]
pub struct RustLiveCoPilot {
    inner: Arc<RwLock<nuxiva_spatial_core::LiveCoPilotEngine>>,
}

#[pymethods]
impl RustLiveCoPilot {
    #[new]
    fn new() -> Self {
        Self {
            inner: Arc::new(RwLock::new(nuxiva_spatial_core::LiveCoPilotEngine::new())),
        }
    }

    fn start_session_json(&self, game_id: &str, initial_state: &str) -> PyResult<String> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        let action = guard.start_session(game_id, initial_state);
        serde_json::to_string(&action).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    fn on_move_applied_json(&self, move_key: &str, board_state: &str) -> PyResult<String> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        let action = guard.on_move_applied(move_key, board_state);
        serde_json::to_string(&action).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    fn end_session_json(&self) -> PyResult<String> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        let action = guard.end_session();
        serde_json::to_string(&action).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    fn is_live(&self) -> PyResult<bool> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        Ok(guard.is_live())
    }
}
