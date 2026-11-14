use std::path::Path;
use std::sync::Arc;

use core_brain::{Dispatched, Dispatcher, load_agents};
use nuxiva_swarm_core::{PlanPrompt, Planner, Settings, SwarmError, SwarmResult};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use serde_json::json;
use tokio::runtime::Handle;

use crate::mcp::RustMcpEngine;

const MAX_REPLY: usize = 256 * 1024;

struct PyPlanner {
    callback: Py<PyAny>,
}

impl Planner for PyPlanner {
    fn propose(&self, prompt: &PlanPrompt) -> SwarmResult<Vec<u8>> {
        let payload = serde_json::to_string(prompt).map_err(|_| SwarmError::PlannerFailed)?;
        let reply: Result<String, PyErr> =
            Python::attach(|py| self.callback.call1(py, (payload,))?.extract(py));
        let text = reply.map_err(|_| SwarmError::PlannerFailed)?;
        if text.len() > MAX_REPLY {
            return Err(SwarmError::PlannerFailed);
        }
        Ok(text.into_bytes())
    }
}

#[pyclass(module = "nuxiva_native", frozen)]
pub struct RustBrain {
    dispatcher: Arc<Dispatcher>,
    handle: Handle,
}

impl std::fmt::Debug for RustBrain {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("RustBrain(..)")
    }
}

fn fail(error: impl std::fmt::Display) -> PyErr {
    PyValueError::new_err(error.to_string())
}

#[pymethods]
impl RustBrain {
    #[new]
    #[pyo3(signature = (engine, agents_dir, planner = None))]
    fn new(engine: &RustMcpEngine, agents_dir: &str, planner: Option<Py<PyAny>>) -> PyResult<Self> {
        let settings = Settings::default();
        let (catalog, index, declared) =
            load_agents(Path::new(agents_dir), &settings).map_err(fail)?;
        let mut dispatcher =
            Dispatcher::new(catalog, settings, index, engine.hub_handle(), declared)
                .map_err(fail)?;
        if let Some(callback) = planner {
            dispatcher = dispatcher.with_planner(Arc::new(PyPlanner { callback }));
        }
        Ok(Self {
            dispatcher: Arc::new(dispatcher),
            handle: engine.runtime_handle(),
        })
    }

    fn dispatch(
        &self,
        py: Python<'_>,
        text: &str,
        principal: &str,
        now_ms: u64,
    ) -> PyResult<String> {
        let dispatcher = Arc::clone(&self.dispatcher);
        let outcome = py
            .detach(|| {
                self.handle
                    .block_on(async move { dispatcher.dispatch(text, principal, now_ms).await })
            })
            .map_err(fail)?;
        let value = match outcome {
            Dispatched::Conversation => json!({"kind": "conversation"}),
            Dispatched::Executed {
                task,
                succeeded,
                steps,
            } => json!({"kind": "executed", "task": task, "succeeded": succeeded, "steps": steps}),
        };
        serde_json::to_string(&value).map_err(fail)
    }

    fn cancel(&self) {
        self.dispatcher.cancel_all();
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustBrain>()?;
    Ok(())
}
