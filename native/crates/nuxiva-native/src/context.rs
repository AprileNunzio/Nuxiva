use nuxiva_context_core::{
    ContextError, ContextSettings, Delta, Lang, PersonId, Request, Sealer, SharedContext,
    person_from_profile,
};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use serde_json::{Value, json};

const MAX_JSON: usize = 16 * 1024 * 1024;

fn fail(error: ContextError) -> PyErr {
    PyValueError::new_err(error.code())
}

fn ids(raw: &[String]) -> PyResult<Vec<PersonId>> {
    raw.iter().map(|s| PersonId::new(s).map_err(fail)).collect()
}

fn lang(code: &str) -> PyResult<Lang> {
    match code {
        "it" => Ok(Lang::It),
        "en" => Ok(Lang::En),
        "fr" => Ok(Lang::Fr),
        "es" => Ok(Lang::Es),
        _ => Err(PyValueError::new_err("unknown language")),
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustUserContext {
    inner: SharedContext,
}

#[pymethods]
#[allow(clippy::needless_pass_by_value)]
impl RustUserContext {
    #[new]
    #[pyo3(signature = (settings_json = ""))]
    fn new(settings_json: &str) -> PyResult<Self> {
        let settings = if settings_json.is_empty() {
            ContextSettings::default()
        } else {
            ContextSettings::from_json(settings_json).map_err(fail)?
        };
        let sealer = Sealer::random().map_err(fail)?;
        Ok(Self {
            inner: SharedContext::new(settings, sealer).map_err(fail)?,
        })
    }

    fn upsert_profile(&self, profile_json: &str) -> PyResult<u64> {
        if profile_json.len() > MAX_JSON {
            return Err(PyValueError::new_err("payload too large"));
        }
        let profile: Value = serde_json::from_str(profile_json)
            .map_err(|_| PyValueError::new_err("invalid json"))?;
        let person = person_from_profile(&profile, self.inner.settings(), self.inner.sealer())
            .map_err(fail)?;
        self.inner
            .apply(Delta::Upsert(Box::new(person)))
            .map_err(fail)
    }

    fn load_profiles(&self, profiles_json: &str) -> PyResult<String> {
        if profiles_json.len() > MAX_JSON {
            return Err(PyValueError::new_err("payload too large"));
        }
        let profiles: Vec<Value> = serde_json::from_str(profiles_json)
            .map_err(|_| PyValueError::new_err("invalid json"))?;
        let mut deltas = Vec::with_capacity(profiles.len());
        let mut rejected = 0_usize;
        for profile in &profiles {
            match person_from_profile(profile, self.inner.settings(), self.inner.sealer()) {
                Ok(person) => deltas.push(Delta::Upsert(Box::new(person))),
                Err(_) => rejected = rejected.saturating_add(1),
            }
        }
        let loaded = deltas.len();
        let version = if deltas.is_empty() {
            self.inner.snapshot().version()
        } else {
            self.inner.apply_all(deltas).map_err(fail)?
        };
        serde_json::to_string(&json!({"loaded": loaded, "rejected": rejected, "version": version}))
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    fn remove(&self, slug: &str) -> PyResult<u64> {
        let id = PersonId::new(slug).map_err(fail)?;
        match self.inner.apply(Delta::Remove(id)) {
            Ok(version) => Ok(version),
            Err(ContextError::Unknown) => Ok(self.inner.snapshot().version()),
            Err(error) => Err(fail(error)),
        }
    }

    fn set_presence(&self, present: Vec<String>, at_ms: u64) -> PyResult<u64> {
        self.inner
            .apply(Delta::SetPresence {
                present: ids(&present)?,
                at_ms,
            })
            .map_err(fail)
    }

    #[pyo3(signature = (subjects, present, lang_code, budget_chars, now_ms))]
    fn render(
        &self,
        py: Python<'_>,
        subjects: Vec<String>,
        present: Vec<String>,
        lang_code: &str,
        budget_chars: usize,
        now_ms: u64,
    ) -> PyResult<String> {
        let request = Request {
            subjects: ids(&subjects)?,
            present: ids(&present)?,
            lang: lang(lang_code)?,
            budget_chars,
            now_ms,
        };
        Ok(py.detach(|| self.inner.render(&request).to_string()))
    }

    fn stats(&self) -> PyResult<String> {
        let snapshot = self.inner.snapshot();
        let bytes: usize = snapshot
            .persons()
            .map(|p| p.approx_bytes())
            .fold(0_usize, usize::saturating_add);
        serde_json::to_string(&json!({
            "version": snapshot.version(),
            "persons": snapshot.len(),
            "present": snapshot.present().len(),
            "approx_bytes": bytes,
        }))
        .map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustUserContext>()
}
