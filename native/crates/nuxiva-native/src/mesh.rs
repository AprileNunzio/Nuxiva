use crate::errors::poisoned;
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use std::sync::RwLock;

#[pyclass(module = "nuxiva_native")]
#[derive(Debug, Default)]
pub struct RustCrdtMesh {
    inner: RwLock<nuxiva_crdt_core::CrdtState>,
}

#[pymethods]
impl RustCrdtMesh {
    #[new]
    fn new() -> Self {
        Self::default()
    }

    fn set(&self, key: &str, value: &str, timestamp_ms: u64, node_id: &str) -> PyResult<bool> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        Ok(guard.set(key, value, timestamp_ms, node_id))
    }

    fn get(&self, key: &str) -> PyResult<Option<String>> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        Ok(guard.get(key).map(str::to_owned))
    }

    fn delete(&self, key: &str, timestamp_ms: u64, node_id: &str) -> PyResult<bool> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        Ok(guard.delete(key, timestamp_ms, node_id))
    }

    fn to_json(&self) -> PyResult<String> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        guard
            .to_json()
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    fn merge_json(&self, remote_json: &str) -> PyResult<usize> {
        let remote = nuxiva_crdt_core::CrdtState::from_json(remote_json)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        Ok(guard.merge(&remote))
    }

    fn active_entries(&self) -> PyResult<std::collections::BTreeMap<String, String>> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        Ok(guard.active_entries())
    }

    fn __len__(&self) -> PyResult<usize> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        Ok(guard.len())
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug, Default)]
pub struct RustP2PStreamManager {
    inner: RwLock<nuxiva_crdt_core::P2PStreamManager>,
}

#[pymethods]
impl RustP2PStreamManager {
    #[new]
    fn new() -> Self {
        Self::default()
    }

    fn register_binding(
        &self,
        satellite_id: &str,
        satellite_ip: &str,
        parent_node_id: &str,
        parent_ip: &str,
        kind_str: &str,
    ) -> PyResult<()> {
        let kind = match kind_str {
            "video" | "rtsp" => nuxiva_crdt_core::StreamKind::VideoRtsp,
            "webrtc" => nuxiva_crdt_core::StreamKind::WebRtc,
            "sensor" => nuxiva_crdt_core::StreamKind::SensorTelemetry,
            _ => nuxiva_crdt_core::StreamKind::AudioPcm,
        };
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        guard.register_binding(satellite_id, satellite_ip, parent_node_id, parent_ip, kind);
        Ok(())
    }

    fn resolve_direct_target(&self, satellite_id: &str) -> PyResult<Option<String>> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        Ok(guard.resolve_direct_target(satellite_id).map(str::to_owned))
    }

    fn record_transfer(&self, satellite_id: &str, bytes: u64) -> PyResult<bool> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        Ok(guard.record_transfer(satellite_id, bytes))
    }
}
