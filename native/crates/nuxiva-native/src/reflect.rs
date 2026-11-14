use std::sync::{Mutex, PoisonError};

use nuxiva_reflect_core::{Catalog, LessonState, ReflectError, Reflection, Settings, Store};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use serde_json::json;

fn fail(error: ReflectError) -> PyErr {
    PyValueError::new_err(error.code())
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustReflect {
    store: Mutex<Store>,
}

impl RustReflect {
    fn with<T>(&self, f: impl FnOnce(&mut Store) -> Result<T, ReflectError>) -> PyResult<T> {
        let mut guard = self.store.lock().unwrap_or_else(PoisonError::into_inner);
        f(&mut guard).map_err(fail)
    }
}

fn state_of(name: &str) -> Result<LessonState, ReflectError> {
    match name {
        "candidate" => Ok(LessonState::Candidate),
        "adopted" => Ok(LessonState::Adopted),
        "rejected" => Ok(LessonState::Rejected),
        "expired" => Ok(LessonState::Expired),
        _ => Err(ReflectError::Invalid),
    }
}

#[pymethods]
impl RustReflect {
    #[new]
    #[pyo3(signature = (settings_json, catalog_json, snapshot_json=None))]
    fn new(settings_json: &str, catalog_json: &str, snapshot_json: Option<&str>) -> PyResult<Self> {
        let settings = if settings_json.is_empty() {
            Settings::default()
        } else {
            Settings::from_json(settings_json).map_err(fail)?
        };
        let catalog = Catalog::from_json(catalog_json).map_err(fail)?;
        let store = match snapshot_json {
            Some(text) if !text.is_empty() => {
                Store::import(settings, catalog, text).map_err(fail)?
            }
            _ => Store::new(settings, catalog).map_err(fail)?,
        };
        Ok(Self {
            store: Mutex::new(store),
        })
    }

    fn record(&self, reflection_json: &str, now_ms: u64) -> PyResult<String> {
        let reflection = Reflection::from_json(reflection_json).map_err(fail)?;
        self.with(|s| {
            let out = s.record(&reflection, now_ms)?;
            Ok(json!({
                "candidate": out.candidate,
                "adopted": out.adopted,
                "blocked": out.blocked,
                "code_request": out.code_request,
            })
            .to_string())
        })
    }

    fn confirm(&self, id: u64, now_ms: u64) -> PyResult<()> {
        self.with(|s| s.confirm(id, now_ms))
    }

    fn reject(&self, id: u64, now_ms: u64) -> PyResult<()> {
        self.with(|s| s.reject(id, now_ms))
    }

    fn revert(&self, kind: &str, now_ms: u64) -> PyResult<()> {
        self.with(|s| s.revert(kind, now_ms))
    }

    fn maintain(&self, now_ms: u64) {
        self.store
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .maintain(now_ms);
    }

    fn lessons(&self, state: &str) -> PyResult<String> {
        let state = state_of(state).map_err(fail)?;
        self.with(|s| serde_json::to_string(&s.lessons(state)).map_err(|_| ReflectError::Serialize))
    }

    fn lesson_for(&self, kind: &str) -> PyResult<Option<String>> {
        self.with(|s| {
            s.lesson_for(kind)
                .map(|l| serde_json::to_string(l).map_err(|_| ReflectError::Serialize))
                .transpose()
        })
    }

    fn take_code_requests(&self) -> PyResult<String> {
        self.with(|s| {
            serde_json::to_string(&s.take_code_requests()).map_err(|_| ReflectError::Serialize)
        })
    }

    fn export(&self) -> PyResult<String> {
        self.with(|s| s.export())
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustReflect>()
}
