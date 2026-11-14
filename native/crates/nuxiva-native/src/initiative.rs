use std::sync::{Mutex, PoisonError};

use nuxiva_initiative_core::{Catalog, Context, Engine, InitiativeError, Settings, Situation};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use serde_json::json;

fn fail(error: InitiativeError) -> PyErr {
    PyValueError::new_err(error.code())
}

fn situation(code: &str) -> PyResult<Situation> {
    match code {
        "idle" => Ok(Situation::Idle),
        "conversation" => Ok(Situation::Conversation),
        "sleeping" => Ok(Situation::Sleeping),
        "guests" => Ok(Situation::Guests),
        "meeting" => Ok(Situation::Meeting),
        _ => Err(fail(InitiativeError::Invalid)),
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustInitiative {
    engine: Mutex<Engine>,
}

impl RustInitiative {
    fn with<T>(&self, f: impl FnOnce(&mut Engine) -> Result<T, InitiativeError>) -> PyResult<T> {
        let mut guard = self.engine.lock().unwrap_or_else(PoisonError::into_inner);
        f(&mut guard).map_err(fail)
    }
}

fn to_json<T: serde::Serialize>(value: &T) -> Result<String, InitiativeError> {
    serde_json::to_string(value).map_err(|_| InitiativeError::Serialize)
}

#[pymethods]
impl RustInitiative {
    #[new]
    #[pyo3(signature = (settings_json, catalog_json, state_json=None))]
    fn new(settings_json: &str, catalog_json: &str, state_json: Option<&str>) -> PyResult<Self> {
        let settings = if settings_json.is_empty() {
            Settings::default()
        } else {
            Settings::from_json(settings_json).map_err(fail)?
        };
        let catalog = Catalog::from_json(catalog_json).map_err(fail)?;
        let mut engine = Engine::new(settings, catalog).map_err(fail)?;
        if let Some(text) = state_json.filter(|t| !t.is_empty()) {
            engine.import_state(text).map_err(fail)?;
        }
        Ok(Self {
            engine: Mutex::new(engine),
        })
    }

    fn observe(
        &self,
        event_json: &str,
        situation_code: &str,
        voice_free: bool,
        now_ms: u64,
    ) -> PyResult<String> {
        let event = Engine::event_from_json(event_json).map_err(fail)?;
        let ctx = Context {
            situation: situation(situation_code)?,
            voice_free,
        };
        self.with(|e| to_json(&e.observe(&event, ctx, now_ms)?))
    }

    fn tick(&self, situation_code: &str, voice_free: bool, now_ms: u64) -> PyResult<String> {
        let ctx = Context {
            situation: situation(situation_code)?,
            voice_free,
        };
        self.with(|e| to_json(&e.tick(ctx, now_ms)))
    }

    fn accept(&self, id: u64, now_ms: u64) -> PyResult<String> {
        self.with(|e| to_json(&e.accept(id, now_ms)?))
    }

    fn refuse(&self, id: u64, now_ms: u64) -> PyResult<()> {
        self.with(|e| e.refuse(id, now_ms))
    }

    fn approve_always(&self, observer: &str) -> PyResult<()> {
        self.with(|e| e.approve_always(observer))
    }

    fn revoke(&self, observer: &str) {
        self.engine
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .revoke(observer);
    }

    fn pending(&self) -> PyResult<String> {
        self.with(|e| to_json(&e.pending()))
    }

    fn diary(&self) -> PyResult<String> {
        self.with(|e| to_json(&e.diary()))
    }

    fn stats(&self) -> PyResult<String> {
        self.with(|e| {
            let s = e.stats();
            Ok(json!({
                "surfaced": s.surfaced,
                "accepted": s.accepted,
                "refused": s.refused,
                "silent": s.silent,
                "capped": s.capped,
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
    m.add_class::<RustInitiative>()
}
