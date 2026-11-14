use std::path::Path;
use std::sync::{Arc, Mutex, PoisonError};

use nuxiva_taskq_core::{
    BoxFuture, CancelToken, ClassCounts, Engine, ErrorPayload, Executor, FileJournal, Journal,
    MemoryJournal, Progress, Settings, Submitted, SystemClock, TaskSpec, TaskqError,
};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use serde_json::{Value, json};

const MAX_JSON: usize = 256 * 1024;
const MAX_EVENTS: usize = 4_096;
const JOURNAL_BYTES: u64 = 64 * 1024 * 1024;
const CODE_BRIDGE: &str = "taskq.bridge.failed";
const CODE_REPLY: &str = "taskq.bridge.reply";

fn fail(error: TaskqError) -> PyErr {
    PyValueError::new_err(error.code())
}

struct BridgeExecutor {
    callback: Py<PyAny>,
}

fn interpret(reply: &str) -> Result<Vec<String>, ErrorPayload> {
    let Ok(Value::Object(object)) = serde_json::from_str::<Value>(reply) else {
        return Err(ErrorPayload::new(CODE_REPLY, false));
    };
    if let Some(error) = object.get("error").and_then(Value::as_object) {
        let code = error
            .get("code")
            .and_then(Value::as_str)
            .unwrap_or(CODE_BRIDGE);
        let transient = error
            .get("transient")
            .and_then(Value::as_bool)
            .unwrap_or(false);
        return Err(ErrorPayload::new(code, transient));
    }
    Ok(object
        .get("evidence")
        .and_then(Value::as_array)
        .map(|list| {
            list.iter()
                .filter_map(Value::as_str)
                .take(64)
                .map(str::to_owned)
                .collect()
        })
        .unwrap_or_default())
}

impl Executor for BridgeExecutor {
    fn run(
        &self,
        spec: TaskSpec,
        cancel: CancelToken,
        progress: Progress,
    ) -> BoxFuture<Result<Vec<String>, ErrorPayload>> {
        let callback = Python::attach(|py| self.callback.clone_ref(py));
        Box::pin(async move {
            let Ok(payload) = spec.to_json() else {
                return Err(ErrorPayload::new(CODE_BRIDGE, false));
            };
            progress.set(1);
            let call = tokio::task::spawn_blocking(move || {
                Python::attach(|py| callback.call1(py, (payload,))?.extract::<String>(py))
            });
            tokio::select! {
                joined = call => match joined {
                    Ok(Ok(text)) => interpret(&text),
                    _ => Err(ErrorPayload::new(CODE_BRIDGE, true)),
                },
                () = cancel.cancelled() => Err(ErrorPayload::new("taskq.cancelled", false)),
            }
        })
    }
}

fn counts(c: ClassCounts) -> Value {
    json!({"queued": c.queued, "running": c.running})
}

#[pyclass(module = "nuxiva_native")]
pub struct RustTaskQueue {
    engine: Mutex<Option<Engine>>,
}

impl std::fmt::Debug for RustTaskQueue {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("RustTaskQueue").finish_non_exhaustive()
    }
}

impl RustTaskQueue {
    fn with<T>(&self, f: impl FnOnce(&Engine) -> PyResult<T>) -> PyResult<T> {
        let guard = self.engine.lock().unwrap_or_else(PoisonError::into_inner);
        match guard.as_ref() {
            Some(engine) => f(engine),
            None => Err(fail(TaskqError::Shutdown)),
        }
    }
}

#[pymethods]
impl RustTaskQueue {
    #[new]
    #[pyo3(signature = (settings_json, handler, journal_path=None))]
    fn new(settings_json: &str, handler: Py<PyAny>, journal_path: Option<&str>) -> PyResult<Self> {
        let settings = if settings_json.is_empty() {
            Settings::default()
        } else {
            Settings::from_json(settings_json).map_err(fail)?
        };
        let journal: Box<dyn Journal> = match journal_path {
            Some(path) if !path.is_empty() => {
                Box::new(FileJournal::open(Path::new(path), JOURNAL_BYTES).map_err(fail)?)
            }
            _ => Box::new(MemoryJournal::new()),
        };
        let executor = Arc::new(BridgeExecutor { callback: handler });
        let engine = Engine::start(settings, executor, journal, Arc::new(SystemClock::new()))
            .map_err(fail)?;
        Ok(Self {
            engine: Mutex::new(Some(engine)),
        })
    }

    fn submit(&self, spec_json: &str) -> PyResult<String> {
        if spec_json.len() > MAX_JSON {
            return Err(fail(TaskqError::TooLarge));
        }
        self.with(
            |engine| match engine.submit_json(spec_json).map_err(fail)? {
                Submitted::Accepted => Ok("accepted".to_owned()),
                Submitted::Duplicate(id) => Ok(format!("duplicate:{id}")),
            },
        )
    }

    fn cancel(&self, id: &str) -> PyResult<()> {
        self.with(|engine| engine.cancel(id).map_err(fail))
    }

    fn status(&self, id: &str) -> PyResult<Option<String>> {
        self.with(|engine| {
            engine
                .status(id)
                .map(|event| serde_json::to_string(&event).map_err(|_| fail(TaskqError::Serialize)))
                .transpose()
        })
    }

    fn events(&self, max: usize) -> PyResult<String> {
        self.with(|engine| {
            serde_json::to_string(&engine.drain_events(max.min(MAX_EVENTS)))
                .map_err(|_| fail(TaskqError::Serialize))
        })
    }

    fn stats(&self) -> PyResult<String> {
        self.with(|engine| {
            let s = engine.stats();
            serde_json::to_string(&json!({
                "voice": counts(s.voice),
                "interactive": counts(s.interactive),
                "background": counts(s.background),
                "maintenance": counts(s.maintenance),
                "journal_errors": s.journal_errors,
                "dropped_events": s.dropped_events,
            }))
            .map_err(|_| fail(TaskqError::Serialize))
        })
    }

    fn shutdown(&self) -> PyResult<()> {
        let mut guard = self.engine.lock().unwrap_or_else(PoisonError::into_inner);
        let Some(mut engine) = guard.take() else {
            return Err(PyRuntimeError::new_err("already stopped"));
        };
        drop(guard);
        Python::attach(|py| py.detach(move || engine.shutdown()));
        Ok(())
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustTaskQueue>()
}
