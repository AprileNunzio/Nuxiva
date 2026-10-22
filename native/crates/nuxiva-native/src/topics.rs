use crate::errors::{poisoned, router_error};
use nuxiva_bus_core::{SubscriptionId, TopicRouter as CoreRouter};
use pyo3::prelude::*;
use std::sync::RwLock;

#[pyclass(frozen, module = "nuxiva_native")]
#[derive(Debug, Default)]
pub(crate) struct TopicRouter {
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
pub(crate) fn matches(pattern: &str, topic: &str) -> bool {
    nuxiva_bus_core::matches(pattern, topic)
}

#[pyfunction]
pub(crate) fn valid_topic(topic: &str) -> bool {
    nuxiva_bus_core::valid_topic(topic)
}

#[pyfunction]
pub(crate) fn valid_pattern(pattern: &str) -> bool {
    nuxiva_bus_core::valid_pattern(pattern)
}

#[pyfunction]
pub(crate) fn valid_origin(origin: &str) -> bool {
    nuxiva_bus_core::valid_origin(origin)
}
