use crate::errors::{poisoned, router_error};
use nuxiva_bus_core::{
    RingBufferLockFree, SubscriptionId, SynapticSpike as CoreSpike,
    SynapticWeightMatrix as CoreWeightMatrix, TopicRouter as CoreRouter, TransmitterType,
};
use pyo3::prelude::*;
use std::sync::RwLock;

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
