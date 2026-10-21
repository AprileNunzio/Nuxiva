#![forbid(unsafe_code)]

mod workbench;

use std::sync::{Arc, RwLock};

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

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustAudioCleaner {
    inner: Arc<RwLock<nuxiva_audio_dsp::AudioCleaner>>,
}

#[pymethods]
impl RustAudioCleaner {
    #[new]
    fn new() -> Self {
        Self {
            inner: Arc::new(RwLock::new(nuxiva_audio_dsp::AudioCleaner::new())),
        }
    }

    fn process_pcm_json(&self, pcm_bytes: &[u8], media_state_json: &str) -> PyResult<String> {
        let media_state: nuxiva_audio_dsp::MediaPlaybackState =
            if media_state_json.trim().is_empty() {
                nuxiva_audio_dsp::MediaPlaybackState::default()
            } else {
                serde_json::from_str(media_state_json)
                    .map_err(|e| PyValueError::new_err(e.to_string()))?
            };

        let num_samples = pcm_bytes.len().saturating_div(2);
        let mut raw_pcm = Vec::with_capacity(num_samples);
        for chunk in pcm_bytes.chunks_exact(2) {
            let b0 = chunk.first().copied().unwrap_or(0);
            let b1 = chunk.get(1).copied().unwrap_or(0);
            raw_pcm.push(i16::from_le_bytes([b0, b1]));
        }

        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        let result = guard.process_frame(&raw_pcm, &media_state);
        serde_json::to_string(&result).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    #[allow(clippy::unused_self)]
    fn compute_rms(&self, pcm_bytes: &[u8]) -> f32 {
        let mut raw_pcm = Vec::with_capacity(pcm_bytes.len().saturating_div(2));
        for chunk in pcm_bytes.chunks_exact(2) {
            let b0 = chunk.first().copied().unwrap_or(0);
            let b1 = chunk.get(1).copied().unwrap_or(0);
            raw_pcm.push(i16::from_le_bytes([b0, b1]));
        }
        nuxiva_audio_dsp::SpectralEntropyVad::compute_rms(&raw_pcm)
    }

    fn reset(&self) -> PyResult<()> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        guard.reset();
        Ok(())
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug, Default)]
pub struct RustDeviceRouter {
    inner: Arc<RwLock<nuxiva_audio_dsp::FailoverDeviceRouter>>,
}

#[pymethods]
impl RustDeviceRouter {
    #[new]
    fn new(is_proximity: bool) -> Self {
        let mode = if is_proximity {
            nuxiva_audio_dsp::DeviceSelectionMode::MultiMicProximity
        } else {
            nuxiva_audio_dsp::DeviceSelectionMode::HierarchicalFallback
        };
        Self {
            inner: Arc::new(RwLock::new(nuxiva_audio_dsp::FailoverDeviceRouter::new(
                mode,
            ))),
        }
    }

    fn register_device_json(&self, device_json: &str) -> PyResult<()> {
        let device: nuxiva_audio_dsp::AudioDevice =
            serde_json::from_str(device_json).map_err(|e| PyValueError::new_err(e.to_string()))?;
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        guard.register_device(device);
        Ok(())
    }

    fn update_connection_state(&self, device_id: &str, is_connected: bool) -> PyResult<()> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        guard.update_connection_state(device_id, is_connected);
        Ok(())
    }

    fn resolve_active_device_json(&self) -> PyResult<Option<String>> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        let dev = guard.resolve_active_device();
        match dev {
            Some(d) => {
                let serialized =
                    serde_json::to_string(d).map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
                Ok(Some(serialized))
            }
            None => Ok(None),
        }
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug, Default)]
pub struct RustMultiMicTriage {
    inner: Arc<RwLock<nuxiva_audio_dsp::MultiMicTriage>>,
}

#[pymethods]
impl RustMultiMicTriage {
    #[new]
    fn new(hysteresis_margin: f32) -> Self {
        Self {
            inner: Arc::new(RwLock::new(nuxiva_audio_dsp::MultiMicTriage::new(
                hysteresis_margin,
            ))),
        }
    }

    fn elect_best_source_json(&self, reports_json: &str) -> PyResult<Option<String>> {
        let reports: Vec<nuxiva_audio_dsp::SatelliteAudioReport> =
            serde_json::from_str(reports_json).map_err(|e| PyValueError::new_err(e.to_string()))?;
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        Ok(guard.elect_best_source(&reports))
    }

    fn reset(&self) -> PyResult<()> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        guard.reset();
        Ok(())
    }
}

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

#[pyclass(module = "nuxiva_native")]
#[derive(Debug, Default)]
pub struct RustResourceGovernor {
    inner: Arc<RwLock<nuxiva_spatial_core::ResourceGovernor>>,
}

#[pymethods]
impl RustResourceGovernor {
    #[new]
    fn new() -> Self {
        Self {
            inner: Arc::new(RwLock::new(nuxiva_spatial_core::ResourceGovernor::new())),
        }
    }

    #[staticmethod]
    fn normalize_ollama_url(raw_host: &str) -> String {
        nuxiva_spatial_core::ResourceGovernor::normalize_ollama_url(raw_host)
    }

    fn register_remote_server(&self, id: &str, raw_host: &str) -> PyResult<()> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        guard.register_remote_server(id, raw_host);
        Ok(())
    }

    fn set_target_allocation(
        &self,
        target_id: &str,
        provider_str: &str,
        model_name: &str,
        node_url: Option<String>,
    ) -> PyResult<()> {
        let provider = match provider_str {
            "ollama_local" => nuxiva_spatial_core::ComputeProvider::OllamaLocal,
            "ollama_remote" => nuxiva_spatial_core::ComputeProvider::OllamaRemote,
            _ => nuxiva_spatial_core::ComputeProvider::ApiKey,
        };
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        guard.set_target_allocation(nuxiva_spatial_core::TargetAllocation {
            target_id: target_id.to_string(),
            provider,
            model_name: model_name.to_string(),
            node_url,
        });
        Ok(())
    }

    #[allow(clippy::needless_pass_by_value)]
    fn apply_global_default_to_all(
        &self,
        provider_str: &str,
        model_name: &str,
        node_url: Option<String>,
    ) -> PyResult<()> {
        let provider = match provider_str {
            "ollama_local" => nuxiva_spatial_core::ComputeProvider::OllamaLocal,
            "ollama_remote" => nuxiva_spatial_core::ComputeProvider::OllamaRemote,
            _ => nuxiva_spatial_core::ComputeProvider::ApiKey,
        };
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        guard.apply_global_default_to_all(provider, model_name, node_url.as_deref());
        Ok(())
    }

    fn evaluate_resource_plan_json(&self) -> PyResult<String> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        let plan = guard.evaluate_resource_plan();
        serde_json::to_string(&plan).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }
}

#[derive(Debug, Default)]
#[pyclass(module = "nuxiva_native")]
pub struct RustMeshTaskGovernor {
    inner: Arc<RwLock<nuxiva_spatial_core::MeshTaskGovernor>>,
}

#[pymethods]
impl RustMeshTaskGovernor {
    #[new]
    fn new() -> Self {
        Self {
            inner: Arc::new(RwLock::new(nuxiva_spatial_core::MeshTaskGovernor::new())),
        }
    }

    fn register_or_update_node_json(&self, profile_json: &str) -> PyResult<()> {
        let profile: nuxiva_spatial_core::NodeProfile = serde_json::from_str(profile_json)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        guard.register_or_update_node(profile);
        Ok(())
    }

    fn get_node_json(&self, node_id: &str) -> PyResult<Option<String>> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        if let Some(profile) = guard.get_node(node_id) {
            let json = serde_json::to_string(profile)
                .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
            Ok(Some(json))
        } else {
            Ok(None)
        }
    }

    fn toggle_component(&self, node_id: &str, component_id: &str, enabled: bool) -> PyResult<bool> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        Ok(guard.toggle_component(node_id, component_id, enabled))
    }

    fn evaluate_node_json(&self, node_id: &str) -> PyResult<Option<String>> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        if let Some(eval) = guard.evaluate_node(node_id) {
            let json =
                serde_json::to_string(&eval).map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
            Ok(Some(json))
        } else {
            Ok(None)
        }
    }

    fn resolve_capability_dispatch_json(
        &self,
        requesting_node_id: &str,
        capability: &str,
    ) -> PyResult<String> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        let res = guard.resolve_capability_dispatch(requesting_node_id, capability);
        serde_json::to_string(&res).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    #[staticmethod]
    fn get_default_components_json(has_gpu: bool) -> PyResult<String> {
        let comps = nuxiva_spatial_core::MeshTaskGovernor::get_default_components(has_gpu);
        serde_json::to_string(&comps).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }
}

#[derive(Debug, Default)]
#[pyclass(module = "nuxiva_native")]
pub struct RustNetworkGovernor {
    inner: Arc<RwLock<nuxiva_spatial_core::NetworkGovernor>>,
}

#[pymethods]
impl RustNetworkGovernor {
    #[new]
    fn new() -> Self {
        Self {
            inner: Arc::new(RwLock::new(nuxiva_spatial_core::NetworkGovernor::new())),
        }
    }

    fn register_or_update_profile_json(&self, profile_json: &str) -> PyResult<()> {
        let prof: nuxiva_spatial_core::NodeNetworkProfile = serde_json::from_str(profile_json)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        guard.register_or_update_profile(prof);
        Ok(())
    }

    fn get_profile_json(&self, node_id: &str) -> PyResult<Option<String>> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        if let Some(prof) = guard.get_profile(node_id) {
            let json =
                serde_json::to_string(prof).map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
            Ok(Some(json))
        } else {
            Ok(None)
        }
    }

    fn set_policy(&self, node_id: &str, policy_str: &str) -> PyResult<bool> {
        let policy = match policy_str {
            "ethernet_only" => nuxiva_spatial_core::ConnectionRoutingPolicy::EthernetOnly,
            "wifi_only" => nuxiva_spatial_core::ConnectionRoutingPolicy::WifiOnly,
            "dual_aggregation" => nuxiva_spatial_core::ConnectionRoutingPolicy::DualAggregation,
            _ => nuxiva_spatial_core::ConnectionRoutingPolicy::Fallback,
        };
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        Ok(guard.set_policy(node_id, policy))
    }

    fn toggle_interface(&self, node_id: &str, interface_name: &str, is_up: bool) -> PyResult<bool> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        Ok(guard.toggle_interface(node_id, interface_name, is_up))
    }

    fn toggle_vpn(&self, node_id: &str, enabled: bool) -> PyResult<bool> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        Ok(guard.toggle_vpn(node_id, enabled))
    }

    #[allow(clippy::too_many_arguments, clippy::needless_pass_by_value)]
    fn update_interface_ip_config(
        &self,
        node_id: &str,
        interface_name: &str,
        mode_str: &str,
        ipv4: Option<String>,
        netmask: Option<String>,
        gateway: Option<String>,
        dns_primary: Option<String>,
        dns_secondary: Option<String>,
    ) -> PyResult<()> {
        let mode = match mode_str {
            "static" => nuxiva_spatial_core::IpAssignmentMode::Static,
            _ => nuxiva_spatial_core::IpAssignmentMode::Dhcp,
        };
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        guard
            .update_interface_ip_config(
                node_id,
                interface_name,
                mode,
                ipv4,
                netmask,
                gateway,
                dns_primary,
                dns_secondary,
            )
            .map_err(PyRuntimeError::new_err)
    }

    fn determine_active_route_json(&self, node_id: &str) -> PyResult<String> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        let route = guard.determine_active_route(node_id);
        serde_json::to_string(&route).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    #[staticmethod]
    fn get_default_profile_json(node_id: &str, node_ip: Option<&str>) -> PyResult<String> {
        let prof = nuxiva_spatial_core::NetworkGovernor::get_default_profile(node_id, node_ip);
        serde_json::to_string(&prof).map_err(|e| PyRuntimeError::new_err(e.to_string()))
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
    m.add_class::<RustSpatialArbiter>()?;
    m.add_class::<RustIntentRouter>()?;
    m.add_class::<RustAudioCleaner>()?;
    m.add_class::<RustDeviceRouter>()?;
    m.add_class::<RustMultiMicTriage>()?;
    m.add_class::<RustFastMemory>()?;
    m.add_class::<RustLiveCoPilot>()?;
    m.add_class::<RustResourceGovernor>()?;
    m.add_class::<RustMeshTaskGovernor>()?;
    m.add_class::<RustNetworkGovernor>()?;
    m.add_class::<workbench::RustWorkbenchTracker>()?;
    m.add_function(wrap_pyfunction!(workbench::validate_netlist_json, m)?)?;
    m.add_function(wrap_pyfunction!(matches, m)?)?;
    m.add_function(wrap_pyfunction!(valid_topic, m)?)?;
    m.add_function(wrap_pyfunction!(valid_pattern, m)?)?;
    m.add_function(wrap_pyfunction!(valid_origin, m)?)?;
    m.add_function(wrap_pyfunction!(detect_language, m)?)?;
    m.add_function(wrap_pyfunction!(supported_languages, m)?)?;
    Ok(())
}
