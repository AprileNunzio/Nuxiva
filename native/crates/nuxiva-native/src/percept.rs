use std::sync::{Mutex, PoisonError};

use nuxiva_context_core::Lang;
use nuxiva_percept_core::{Fuser, Fusion, Observation, PerceptError, PerceptSettings};
use nuxiva_swarm_core::{Channel, Ident, Settings};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use serde_json::json;

use crate::context::RustUserContext;

const MAX_JSON: usize = 64 * 1024;
const MAX_TEXT: usize = 64 * 1024;

fn fail(error: &PerceptError) -> PyErr {
    PyValueError::new_err(error.code())
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

fn channel(code: &str) -> PyResult<Channel> {
    match code {
        "voice" => Ok(Channel::Voice),
        "text" => Ok(Channel::Text),
        "vision" => Ok(Channel::Vision),
        "event" => Ok(Channel::Event),
        _ => Err(PyValueError::new_err("unknown channel")),
    }
}

#[derive(Debug, serde::Deserialize)]
#[serde(deny_unknown_fields)]
struct FuseRequest {
    id: String,
    channel: String,
    text: String,
    lang: String,
    #[serde(default)]
    budget_chars: usize,
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustPercept {
    fuser: Mutex<Fuser>,
    fusion: Fusion,
    limits: Settings,
}

#[pymethods]
impl RustPercept {
    #[new]
    #[pyo3(signature = (context, settings_json = ""))]
    fn new(context: &Bound<'_, RustUserContext>, settings_json: &str) -> PyResult<Self> {
        let settings = if settings_json.is_empty() {
            PerceptSettings::default()
        } else {
            PerceptSettings::from_json(settings_json).map_err(|e| fail(&e))?
        };
        Ok(Self {
            fuser: Mutex::new(Fuser::new(settings).map_err(|e| fail(&e))?),
            fusion: Fusion::new(context.borrow().inner.clone()),
            limits: Settings::default(),
        })
    }

    fn observe(&self, observation_json: &str, now_ms: u64) -> PyResult<()> {
        if observation_json.len() > MAX_JSON {
            return Err(PyValueError::new_err("payload too large"));
        }
        let observation: Observation = serde_json::from_str(observation_json)
            .map_err(|_| PyValueError::new_err("invalid json"))?;
        self.fuser
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .observe(observation, now_ms)
            .map_err(|e| fail(&e))
    }

    fn fuse(&self, py: Python<'_>, request_json: &str, now_ms: u64) -> PyResult<String> {
        if request_json.len() > MAX_TEXT {
            return Err(PyValueError::new_err("payload too large"));
        }
        let request: FuseRequest = serde_json::from_str(request_json)
            .map_err(|_| PyValueError::new_err("invalid json"))?;
        let FuseRequest {
            id: percept_id,
            channel: channel_code,
            text,
            lang: lang_code,
            budget_chars,
        } = request;
        let id = Ident::new(&percept_id).map_err(|_| PyValueError::new_err("invalid id"))?;
        let channel = channel(&channel_code)?;
        let lang = lang(&lang_code)?;
        let percept = self
            .fuser
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .fuse(id, channel, text, now_ms, &self.limits)
            .map_err(|e| fail(&e))?;
        let view = py
            .detach(|| self.fusion.view(&percept, lang, budget_chars))
            .map_err(|e| fail(&e))?;
        serde_json::to_string(&json!({
            "speaker": percept.speaker.as_ref().map(Ident::as_str),
            "addressee_permille": percept.addressee_permille,
            "presence": percept.presence.iter().map(Ident::as_str).collect::<Vec<_>>(),
            "has_emotion": percept.emotion.is_some(),
            "view": &*view,
        }))
        .map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustPercept>()
}
