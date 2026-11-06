use std::sync::Mutex;

use nuxiva_supervisor_core::{LoopBook, Outcome, Policy};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;

use crate::errors::poisoned;

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug, Default)]
pub struct RustLoopBook {
    inner: Mutex<LoopBook>,
}

impl RustLoopBook {
    fn with<T>(&self, f: impl FnOnce(&mut LoopBook) -> T) -> PyResult<T> {
        let mut book = self.inner.lock().map_err(|_| poisoned())?;
        Ok(f(&mut book))
    }
}

#[pymethods]
impl RustLoopBook {
    #[new]
    fn new() -> Self {
        Self::default()
    }

    fn add(&self, name: &str, period: f64, now: f64) -> PyResult<bool> {
        self.with(|b| b.add(name, period, now))
    }

    fn start(&self, name: &str, now: f64) -> PyResult<bool> {
        self.with(|b| b.start(name, now))
    }

    fn beat(&self, name: &str, now: f64) -> PyResult<bool> {
        self.with(|b| b.beat(name, now))
    }

    #[allow(clippy::too_many_arguments)]
    #[pyo3(signature = (name, outcome, reason, now, restart_enabled, backoff_min, backoff_max, stable_after, report_every))]
    fn exit(
        &self,
        name: &str,
        outcome: &str,
        reason: &str,
        now: f64,
        restart_enabled: bool,
        backoff_min: f64,
        backoff_max: f64,
        stable_after: f64,
        report_every: u64,
    ) -> PyResult<Option<(&'static str, f64, bool, u64)>> {
        let outcome = Outcome::parse(outcome)
            .ok_or_else(|| PyValueError::new_err("loops.outcome.invalid"))?;
        let policy = Policy {
            restart_enabled,
            backoff_min,
            backoff_max,
            stable_after,
            report_every,
        };
        self.with(|b| {
            b.exit(name, outcome, reason, now, policy)
                .map(|d| (d.action.code(), d.delay, d.report, d.restarts))
        })
    }

    fn stalled(&self, now: f64, stale_factor: f64) -> PyResult<Vec<String>> {
        self.with(|b| b.stalled(now, stale_factor))
    }

    fn snapshot(&self, now: f64) -> PyResult<String> {
        let views = self.with(|b| b.snapshot(now))?;
        serde_json::to_string(&views).map_err(|_| PyRuntimeError::new_err("loops.serialize"))
    }

    fn totals(&self) -> PyResult<String> {
        let totals = self.with(|b| b.totals())?;
        serde_json::to_string(&totals).map_err(|_| PyRuntimeError::new_err("loops.serialize"))
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustLoopBook>()?;
    Ok(())
}
