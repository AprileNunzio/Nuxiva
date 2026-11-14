use std::sync::{Mutex, PoisonError};

use nuxiva_proactivity_core::{Engine, ProactivityError, Ruleset, Settings};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use serde_json::json;

fn fail(error: ProactivityError) -> PyErr {
    PyValueError::new_err(error.code())
}

fn to_json<T: serde::Serialize>(value: &T) -> Result<String, ProactivityError> {
    serde_json::to_string(value).map_err(|_| ProactivityError::Serialize)
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustProactivity {
    engine: Mutex<Engine>,
}

impl RustProactivity {
    fn with<T>(&self, f: impl FnOnce(&mut Engine) -> Result<T, ProactivityError>) -> PyResult<T> {
        let mut guard = self.engine.lock().unwrap_or_else(PoisonError::into_inner);
        f(&mut guard).map_err(fail)
    }
}

#[pymethods]
impl RustProactivity {
    #[new]
    #[pyo3(signature = (settings_json, rules_json, state_json=None))]
    fn new(settings_json: &str, rules_json: &str, state_json: Option<&str>) -> PyResult<Self> {
        let settings = if settings_json.is_empty() {
            Settings::default()
        } else {
            Settings::from_json(settings_json).map_err(fail)?
        };
        let rules = Ruleset::from_json(rules_json).map_err(fail)?;
        let mut engine = Engine::new(settings, rules).map_err(fail)?;
        if let Some(text) = state_json.filter(|t| !t.is_empty()) {
            engine.import_state(text).map_err(fail)?;
        }
        Ok(Self {
            engine: Mutex::new(engine),
        })
    }

    fn ingest(&self, signal_json: &str, context_json: &str, now_ms: u64) -> PyResult<String> {
        let signal = Engine::signal_from_json(signal_json).map_err(fail)?;
        let ctx = Engine::context_from_json(context_json).map_err(fail)?;
        self.with(|e| to_json(&e.ingest(&signal, &ctx, now_ms)?))
    }

    fn forecast(&self, forecast_json: &str, context_json: &str, now_ms: u64) -> PyResult<String> {
        let forecast = Engine::forecast_from_json(forecast_json).map_err(fail)?;
        let ctx = Engine::context_from_json(context_json).map_err(fail)?;
        self.with(|e| to_json(&e.forecast(&forecast, &ctx, now_ms)?))
    }

    fn tick(&self, context_json: &str, now_ms: u64) -> PyResult<String> {
        let ctx = Engine::context_from_json(context_json).map_err(fail)?;
        self.with(|e| to_json(&e.tick(&ctx, now_ms)?))
    }

    fn accept(&self, id: u64, now_ms: u64) -> PyResult<String> {
        self.with(|e| to_json(&e.accept(id, now_ms)?))
    }

    fn refuse(&self, id: u64, now_ms: u64) -> PyResult<()> {
        self.with(|e| e.refuse(id, now_ms))
    }

    fn dismiss(&self, id: u64) -> PyResult<()> {
        self.with(|e| e.dismiss(id))
    }

    fn undo(&self, id: u64, now_ms: u64) -> PyResult<String> {
        self.with(|e| to_json(&e.undo(id, now_ms)?))
    }

    fn approve_always(&self, rule: &str) -> PyResult<()> {
        self.with(|e| e.approve_always(rule))
    }

    fn revoke(&self, rule: &str) {
        self.engine
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .revoke(rule);
    }

    fn set_policy(&self, person: &str, policy_json: &str) -> PyResult<()> {
        let policy = Engine::policy_from_json(policy_json).map_err(fail)?;
        self.with(|e| e.set_policy(person, policy))
    }

    #[pyo3(signature = (rule, person=None))]
    fn reset_learning(&self, rule: &str, person: Option<&str>) {
        self.engine
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .reset_learning(rule, person);
    }

    fn pending(&self) -> PyResult<String> {
        self.with(|e| to_json(&e.pending()))
    }

    fn log(&self) -> PyResult<String> {
        self.with(|e| to_json(&e.log()))
    }

    fn explain(&self, id: u64) -> PyResult<String> {
        self.with(|e| to_json(e.explain(id)?))
    }

    fn undoable(&self) -> PyResult<String> {
        self.with(|e| to_json(&e.undoable()))
    }

    fn stats(&self) -> PyResult<String> {
        self.with(|e| {
            let s = e.stats();
            Ok(json!({
                "surfaced": s.surfaced,
                "accepted": s.accepted,
                "refused": s.refused,
                "undone": s.undone,
                "silent": s.silent,
                "capped": s.capped,
                "blocked": s.blocked,
                "expired": s.expired,
                "acceptance_permille": e.acceptance_permille(),
            })
            .to_string())
        })
    }

    fn export_state(&self) -> PyResult<String> {
        self.with(|e| e.export_state())
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustProactivity>()
}
