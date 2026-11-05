use crate::errors::poisoned;
use nuxiva_display_learner::store::{open, seal};
use nuxiva_display_learner::{ContextVector, FeedbackSample, Learner, LearnerPolicy, ScreenRole};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use serde::Deserialize;
use std::collections::BTreeMap;
use std::sync::Mutex;

const MAX_INPUT: usize = 256 * 1024;
const MAX_WIDGETS: usize = 512;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Query {
    #[serde(default)]
    person: Option<String>,
    #[serde(default)]
    guests: bool,
    #[serde(default)]
    context: ContextVector,
    now_ms: u64,
    #[serde(default)]
    tick: u64,
    widgets: Vec<String>,
}

fn bad<E: std::fmt::Display>(e: E) -> PyErr {
    PyValueError::new_err(e.to_string())
}

fn sized(raw: &str) -> PyResult<&str> {
    if raw.len() > MAX_INPUT {
        Err(PyValueError::new_err("learner input too large"))
    } else {
        Ok(raw)
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustLearner {
    inner: Mutex<Learner>,
}

#[pymethods]
impl RustLearner {
    #[new]
    #[pyo3(signature = (policy_json = None))]
    fn new(policy_json: Option<&str>) -> PyResult<Self> {
        let policy: LearnerPolicy = match policy_json {
            Some(raw) => serde_json::from_str(sized(raw)?).map_err(bad)?,
            None => LearnerPolicy::default(),
        };
        Ok(Self {
            inner: Mutex::new(Learner::new(policy).map_err(bad)?),
        })
    }

    fn observe(&self, sample_json: &str) -> PyResult<String> {
        let sample: FeedbackSample = serde_json::from_str(sized(sample_json)?).map_err(bad)?;
        let outcome = self
            .inner
            .lock()
            .map_err(|_| poisoned())?
            .observe(&sample)
            .map_err(bad)?;
        serde_json::to_string(&outcome).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    fn affinities(&self, query_json: &str) -> PyResult<String> {
        let q: Query = serde_json::from_str(sized(query_json)?).map_err(bad)?;
        if q.widgets.len() > MAX_WIDGETS {
            return Err(PyValueError::new_err("too many widgets"));
        }
        let learner = self.inner.lock().map_err(|_| poisoned())?;
        let out: BTreeMap<&str, _> = q
            .widgets
            .iter()
            .map(|w| {
                let a = learner.affinity(
                    q.person.as_deref(),
                    w,
                    &q.context,
                    q.now_ms,
                    q.tick,
                    q.guests,
                );
                (w.as_str(), a)
            })
            .collect();
        serde_json::to_string(&out).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    fn placement(&self, person: &str, widget: &str, role: &str, now_ms: u64) -> PyResult<String> {
        let role: ScreenRole =
            serde_json::from_value(serde_json::Value::String(role.to_owned())).map_err(bad)?;
        let (cell, size) = self.inner.lock().map_err(|_| poisoned())?.placement(
            Some(person),
            widget,
            role,
            now_ms,
        );
        serde_json::to_string(&serde_json::json!({"cell": cell, "size": size}))
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    #[pyo3(signature = (person = None))]
    fn metrics(&self, person: Option<&str>) -> PyResult<Option<String>> {
        let metrics = self.inner.lock().map_err(|_| poisoned())?.metrics(person);
        metrics
            .map(|m| serde_json::to_string(&m).map_err(|e| PyRuntimeError::new_err(e.to_string())))
            .transpose()
    }

    fn reset(&self, person: &str) -> PyResult<bool> {
        self.inner
            .lock()
            .map_err(|_| poisoned())?
            .reset(person)
            .map_err(bad)
    }

    fn forget_session(&self) -> PyResult<()> {
        self.inner.lock().map_err(|_| poisoned())?.forget_session();
        Ok(())
    }

    fn take_dirty(&self) -> PyResult<Vec<String>> {
        Ok(self.inner.lock().map_err(|_| poisoned())?.take_dirty())
    }

    fn persons(&self) -> PyResult<Vec<String>> {
        Ok(self.inner.lock().map_err(|_| poisoned())?.persons())
    }

    fn export_sealed<'py>(
        &self,
        py: Python<'py>,
        master: &[u8],
        person: &str,
    ) -> PyResult<Bound<'py, PyBytes>> {
        let raw = self
            .inner
            .lock()
            .map_err(|_| poisoned())?
            .export(person)
            .map_err(bad)?;
        let sealed = seal(master, person, &raw).map_err(bad)?;
        Ok(PyBytes::new(py, &sealed))
    }

    fn import_sealed(&self, master: &[u8], person: &str, blob: &[u8]) -> PyResult<()> {
        let raw = open(master, person, blob).map_err(bad)?;
        self.inner
            .lock()
            .map_err(|_| poisoned())?
            .import(person, &raw)
            .map_err(bad)
    }
}
