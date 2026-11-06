use std::sync::{Mutex, MutexGuard};

use nuxiva_rescue_core::{Engine, Evidence, Kind, MAX_EVIDENCE, Policy, Step, assess};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;

const MAX_JSON: usize = 262_144;

fn kind_of(raw: &str) -> PyResult<Kind> {
    serde_json::from_value(serde_json::Value::String(raw.to_owned()))
        .map_err(|_| PyValueError::new_err("rescue.evidence.kind"))
}

fn finite(now: f64) -> PyResult<f64> {
    if now.is_finite() && now >= 0.0 {
        Ok(now)
    } else {
        Err(PyValueError::new_err("rescue.evidence.time"))
    }
}

fn to_json<T: serde::Serialize>(value: &T) -> PyResult<String> {
    serde_json::to_string(value).map_err(|_| PyRuntimeError::new_err("rescue.encode"))
}

fn policy_of(raw: &str) -> PyResult<Policy> {
    Policy::from_json(raw).map_err(|e| PyValueError::new_err(e.code()))
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustRescue {
    inner: Mutex<Engine>,
}

impl RustRescue {
    fn engine(&self) -> PyResult<MutexGuard<'_, Engine>> {
        self.inner
            .lock()
            .map_err(|_| PyRuntimeError::new_err("rescue.poisoned"))
    }

    fn run(&self, f: impl FnOnce(&mut Engine) -> Step) -> PyResult<String> {
        let mut engine = self.engine()?;
        to_json(&f(&mut engine))
    }
}

#[pymethods]
impl RustRescue {
    #[new]
    #[pyo3(signature = (policy=""))]
    fn new(policy: &str) -> PyResult<Self> {
        Ok(Self {
            inner: Mutex::new(Engine::new(policy_of(policy)?)),
        })
    }

    #[allow(clippy::too_many_arguments)]
    #[pyo3(signature = (kind, probability, confidence, source, at, now, room=None))]
    fn observe(
        &self,
        kind: &str,
        probability: f64,
        confidence: f64,
        source: String,
        at: f64,
        now: f64,
        room: Option<String>,
    ) -> PyResult<()> {
        let evidence = Evidence {
            kind: kind_of(kind)?,
            probability,
            confidence,
            source,
            room,
            at,
        };
        self.engine()?
            .observe(evidence, finite(now)?)
            .map_err(|e| PyValueError::new_err(e.code()))
    }

    fn update(&self, now: f64) -> PyResult<String> {
        let now = finite(now)?;
        self.run(|e| e.update(now))
    }

    fn person_ok(&self, now: f64) -> PyResult<String> {
        let now = finite(now)?;
        self.run(|e| e.person_ok(now))
    }

    fn need_help(&self, now: f64) -> PyResult<String> {
        let now = finite(now)?;
        self.run(|e| e.need_help(now))
    }

    fn acknowledge(&self, tier: u8, now: f64) -> PyResult<String> {
        let now = finite(now)?;
        self.run(|e| e.acknowledge(tier, now))
    }

    fn dismiss(&self, now: f64) -> PyResult<String> {
        let now = finite(now)?;
        self.run(|e| e.dismiss(now))
    }

    fn timeline(&self) -> PyResult<String> {
        to_json(&self.engine()?.timeline())
    }

    fn policy(&self) -> PyResult<String> {
        to_json(self.engine()?.policy())
    }
}

#[pyfunction]
fn rescue_assess(evidence: &str, now: f64, policy: &str) -> PyResult<String> {
    if evidence.len() > MAX_JSON {
        return Err(PyValueError::new_err("rescue.evidence.too_large"));
    }
    let now = finite(now)?;
    let policy = policy_of(policy)?;
    let list: Vec<Evidence> = serde_json::from_str(evidence)
        .map_err(|_| PyValueError::new_err("rescue.evidence.format"))?;
    if list.len() > MAX_EVIDENCE {
        return Err(PyValueError::new_err("rescue.evidence.too_many"));
    }
    for e in &list {
        e.validate(now)
            .map_err(|err| PyValueError::new_err(err.code()))?;
    }
    to_json(&assess(&list, &policy, now))
}

#[pyfunction]
fn rescue_policy(policy: &str) -> PyResult<String> {
    to_json(&policy_of(policy)?)
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustRescue>()?;
    m.add_function(wrap_pyfunction!(rescue_assess, m)?)?;
    m.add_function(wrap_pyfunction!(rescue_policy, m)?)
}
