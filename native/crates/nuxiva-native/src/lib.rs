#![forbid(unsafe_code)]

use std::sync::RwLock;

use nuxiva_bus_core::{
    RingBufferLockFree, RouterError, SubscriptionId, SynapticSpike as CoreSpike,
    SynapticWeightMatrix as CoreWeightMatrix, TopicRouter as CoreRouter, TransmitterType,
};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;

fn router_error(error: RouterError) -> PyErr {
    match error {
        RouterError::Topic(inner) => PyValueError::new_err(inner.to_string()),
        RouterError::CapacityExhausted => PyRuntimeError::new_err(error.to_string()),
    }
}

fn poisoned() -> PyErr {
    PyRuntimeError::new_err("state is poisoned")
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug, Clone, Copy)]
pub struct PySynapticSpike {
    #[pyo3(get, set)]
    pub source_neuron: u32,
    #[pyo3(get, set)]
    pub target_cluster: u32,
    #[pyo3(get, set)]
    pub potential: f32,
    #[pyo3(get, set)]
    pub inhibitory_gaba: bool,
    #[pyo3(get, set)]
    pub emotion_vector: [f32; 4],
    #[pyo3(get, set)]
    pub payload_id: u64,
}

#[pymethods]
impl PySynapticSpike {
    #[new]
    #[pyo3(signature = (source_neuron, target_cluster, potential, inhibitory_gaba = false, emotion_vector = [0.0, 0.0, 0.0, 0.0], payload_id = 0))]
    fn new(
        source_neuron: u32,
        target_cluster: u32,
        potential: f32,
        inhibitory_gaba: bool,
        emotion_vector: [f32; 4],
        payload_id: u64,
    ) -> Self {
        Self {
            source_neuron,
            target_cluster,
            potential,
            inhibitory_gaba,
            emotion_vector,
            payload_id,
        }
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct SynapticWeightMatrix {
    inner: RwLock<CoreWeightMatrix>,
}

#[pymethods]
impl SynapticWeightMatrix {
    #[new]
    #[pyo3(signature = (rows, cols, default_weight = 0.5))]
    fn new(rows: usize, cols: usize, default_weight: f32) -> Self {
        Self {
            inner: RwLock::new(CoreWeightMatrix::new(rows, cols, default_weight)),
        }
    }

    fn get(&self, pre: usize, post: usize) -> PyResult<f32> {
        Ok(self.inner.read().map_err(|_| poisoned())?.get(pre, post))
    }

    fn set(&self, pre: usize, post: usize, weight: f32) -> PyResult<()> {
        self.inner
            .write()
            .map_err(|_| poisoned())?
            .set(pre, post, weight);
        Ok(())
    }

    fn apply_stdp(
        &self,
        pre: usize,
        post: usize,
        delta_t_ms: f32,
        dopamine: f32,
        is_reward: bool,
    ) -> PyResult<f32> {
        Ok(self
            .inner
            .write()
            .map_err(|_| poisoned())?
            .apply_stdp(pre, post, delta_t_ms, dopamine, is_reward))
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustSynapticBus {
    router: RwLock<CoreRouter>,
    ring: RwLock<RingBufferLockFree<CoreSpike>>,
}

#[pymethods]
impl RustSynapticBus {
    #[new]
    fn new() -> Self {
        Self {
            router: RwLock::new(CoreRouter::default()),
            ring: RwLock::new(RingBufferLockFree::new()),
        }
    }

    fn subscribe(&self, pattern: &str) -> PyResult<SubscriptionId> {
        self.router
            .write()
            .map_err(|_| poisoned())?
            .subscribe(pattern)
            .map_err(router_error)
    }

    fn unsubscribe(&self, id: SubscriptionId) -> PyResult<bool> {
        Ok(self.router.write().map_err(|_| poisoned())?.unsubscribe(id))
    }

    fn push_spike(&self, spike: PySynapticSpike) -> PyResult<bool> {
        let transmitter = if spike.inhibitory_gaba {
            TransmitterType::GabaInhibitory
        } else {
            TransmitterType::GlutamateExcitatory
        };
        let core_spike = CoreSpike::new(
            spike.source_neuron,
            spike.target_cluster,
            spike.potential,
            transmitter,
            spike.emotion_vector,
            spike.payload_id,
        );
        Ok(self.ring.write().map_err(|_| poisoned())?.push(core_spike))
    }

    fn pop_spike(&self) -> PyResult<Option<PySynapticSpike>> {
        let item = self.ring.write().map_err(|_| poisoned())?.pop();
        Ok(item.map(|s| PySynapticSpike {
            source_neuron: s.source_neuron,
            target_cluster: s.target_cluster,
            potential: s.potential,
            inhibitory_gaba: s.is_inhibitory(),
            emotion_vector: s.emotion_vector,
            payload_id: s.payload_id,
        }))
    }

    fn queue_len(&self) -> PyResult<usize> {
        Ok(self.ring.read().map_err(|_| poisoned())?.len())
    }
}

#[pyclass(frozen, module = "nuxiva_native")]
#[derive(Debug, Default)]
struct TopicRouter {
    inner: RwLock<CoreRouter>,
}

#[pymethods]
impl TopicRouter {
    #[new]
    fn new() -> Self {
        Self::default()
    }

    fn subscribe(&self, pattern: &str) -> PyResult<SubscriptionId> {
        self.inner
            .write()
            .map_err(|_| poisoned())?
            .subscribe(pattern)
            .map_err(router_error)
    }

    fn unsubscribe(&self, id: SubscriptionId) -> PyResult<bool> {
        Ok(self.inner.write().map_err(|_| poisoned())?.unsubscribe(id))
    }

    fn route(&self, py: Python<'_>, topic: &str) -> PyResult<Vec<SubscriptionId>> {
        py.detach(|| {
            self.inner
                .read()
                .map_err(|_| poisoned())?
                .route(topic)
                .map_err(router_error)
        })
    }

    fn __len__(&self) -> PyResult<usize> {
        Ok(self.inner.read().map_err(|_| poisoned())?.len())
    }
}

#[pyfunction]
fn matches(pattern: &str, topic: &str) -> bool {
    nuxiva_bus_core::matches(pattern, topic)
}

#[pyfunction]
fn valid_topic(topic: &str) -> bool {
    nuxiva_bus_core::valid_topic(topic)
}

#[pyfunction]
fn valid_pattern(pattern: &str) -> bool {
    nuxiva_bus_core::valid_pattern(pattern)
}

#[pyfunction]
fn valid_origin(origin: &str) -> bool {
    nuxiva_bus_core::valid_origin(origin)
}

#[pyfunction]
#[pyo3(signature = (text, allowed = ""))]
fn detect_language(py: Python<'_>, text: &str, allowed: &str) -> Option<(String, f64, bool)> {
    py.detach(|| {
        let codes: Vec<&str> = allowed
            .split(',')
            .map(str::trim)
            .filter(|c| !c.is_empty())
            .collect();
        nuxiva_langid::detect(text, &codes).map(|g| (g.code.to_owned(), g.confidence, g.reliable))
    })
}

#[pyfunction]
fn supported_languages() -> Vec<&'static str> {
    nuxiva_langid::supported()
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct FastScanner {
    inner: nuxiva_bus_core::FastScannerRegistry,
}

#[pymethods]
impl FastScanner {
    #[new]
    fn new() -> Self {
        Self {
            inner: nuxiva_bus_core::FastScannerRegistry::new(),
        }
    }

    fn scan(&self, py: Python<'_>, root_dir: &str, target_file: &str) -> PyResult<Py<PyAny>> {
        let report = self.inner.scan_directory(root_dir, target_file);
        let dict = pyo3::types::PyDict::new(py);
        dict.set_item("total", report.total)?;
        dict.set_item("added", report.added)?;
        dict.set_item("modified", report.modified)?;
        dict.set_item("removed", report.removed)?;
        let entries = pyo3::types::PyList::empty(py);
        for e in report.entries {
            let entry_dict = pyo3::types::PyDict::new(py);
            entry_dict.set_item("id", e.id)?;
            entry_dict.set_item("path", e.path)?;
            entry_dict.set_item("fingerprint", e.fingerprint)?;
            entry_dict.set_item("is_dir", e.is_dir)?;
            entries.append(entry_dict)?;
        }
        dict.set_item("entries", entries)?;
        Ok(dict.into())
    }

    fn invalidate(&self, id: &str) -> bool {
        self.inner.invalidate(id)
    }

    fn clear(&self) {
        self.inner.clear();
    }
}

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

#[pymodule(gil_used = false)]
fn nuxiva_native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add("MAX_SUBSCRIPTIONS", nuxiva_bus_core::MAX_SUBSCRIPTIONS)?;
    m.add_class::<TopicRouter>()?;
    m.add_class::<RustSynapticBus>()?;
    m.add_class::<SynapticWeightMatrix>()?;
    m.add_class::<PySynapticSpike>()?;
    m.add_class::<FastScanner>()?;
    m.add_class::<RustCrdtMesh>()?;
    m.add_class::<RustP2PStreamManager>()?;
    m.add_function(wrap_pyfunction!(matches, m)?)?;
    m.add_function(wrap_pyfunction!(valid_topic, m)?)?;
    m.add_function(wrap_pyfunction!(valid_pattern, m)?)?;
    m.add_function(wrap_pyfunction!(valid_origin, m)?)?;
    m.add_function(wrap_pyfunction!(detect_language, m)?)?;
    m.add_function(wrap_pyfunction!(supported_languages, m)?)?;
    Ok(())
}
