use std::collections::HashMap;
use std::sync::{Mutex, PoisonError};

use nuxiva_loop_core::{
    Artifact, ArtifactDraft, Coder, Critic, CriticReport, Decision, Feedback, Gate, LoopError,
    LoopResult, Outcome, Permit, Settings, Target, parse, run,
};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

fn fail(error: LoopError) -> PyErr {
    PyValueError::new_err(error.code())
}

struct PyCoder<'a> {
    callback: &'a Py<PyAny>,
}

struct PyCritic<'a> {
    callback: &'a Py<PyAny>,
}

impl Coder for PyCoder<'_> {
    fn produce(
        &mut self,
        feedback: Option<&Feedback>,
        iteration: u32,
    ) -> LoopResult<ArtifactDraft> {
        let payload = match feedback {
            Some(f) => serde_json::to_string(f).map_err(|_| LoopError::Serialize)?,
            None => String::new(),
        };
        let reply: String = Python::attach(|py| {
            self.callback
                .call1(py, (payload, iteration))?
                .extract::<String>(py)
        })
        .map_err(|_| LoopError::Coder)?;
        parse(&reply)
    }
}

impl Critic for PyCritic<'_> {
    fn evaluate(&mut self, artifact: &Artifact, iteration: u32) -> LoopResult<CriticReport> {
        let payload = serde_json::to_string(artifact).map_err(|_| LoopError::Serialize)?;
        let reply: String = Python::attach(|py| {
            self.callback
                .call1(py, (payload, iteration))?
                .extract::<String>(py)
        })
        .map_err(|_| LoopError::Critic)?;
        parse(&reply)
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustCoderLoop {
    settings: Settings,
    gate: Gate,
    permits: Mutex<HashMap<String, Permit>>,
}

#[pymethods]
impl RustCoderLoop {
    #[new]
    #[pyo3(signature = (settings_json=""))]
    fn new(settings_json: &str) -> PyResult<Self> {
        let settings = if settings_json.is_empty() {
            Settings::default()
        } else {
            Settings::from_json(settings_json).map_err(fail)?
        };
        let gate = Gate::new(settings.clone()).map_err(fail)?;
        Ok(Self {
            settings,
            gate,
            permits: Mutex::new(HashMap::new()),
        })
    }

    fn run(
        &self,
        py: Python<'_>,
        coder: &Bound<'_, PyAny>,
        critic: &Bound<'_, PyAny>,
    ) -> PyResult<String> {
        let coder = coder.clone().unbind();
        let critic = critic.clone().unbind();
        let settings = self.settings.clone();
        let outcome = py
            .detach(|| {
                let mut c = PyCoder { callback: &coder };
                let mut k = PyCritic { callback: &critic };
                run(&settings, &mut c, &mut k)
            })
            .map_err(fail)?;
        if let Some(permit) = self.gate.issue(&outcome) {
            if let Outcome::Passed { artifact, .. } = &outcome {
                self.permits
                    .lock()
                    .unwrap_or_else(PoisonError::into_inner)
                    .insert(artifact.digest.clone(), permit);
            }
        }
        serde_json::to_string(&outcome).map_err(|_| fail(LoopError::Serialize))
    }

    fn authorize(&self, digest: &str, target_json: &str, consent: bool) -> PyResult<&'static str> {
        let target: Target = parse(target_json).map_err(fail)?;
        let permits = self.permits.lock().unwrap_or_else(PoisonError::into_inner);
        let decision = self
            .gate
            .authorize(permits.get(digest), digest, &target, consent);
        Ok(match decision {
            Decision::Allowed => "allowed",
            Decision::NeedsConsent => "needs_consent",
            Decision::Denied => "denied",
        })
    }

    fn revoke(&self, digest: &str) {
        self.gate.revoke(digest);
        self.permits
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .remove(digest);
    }

    fn audit(&self) -> PyResult<String> {
        serde_json::to_string(&self.gate.audit()).map_err(|_| fail(LoopError::Serialize))
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustCoderLoop>()
}
