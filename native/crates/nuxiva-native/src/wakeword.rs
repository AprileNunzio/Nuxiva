use std::sync::Mutex;

use nuxiva_wakeword_core::{Config, Decision, Detector, Model, Policy, Speaker, decide};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyBytes;

const MAX_PCM_BYTES: usize = 16_000 * 2 * 30;
const MAX_MODEL_BYTES: usize = 2 * 1024 * 1024;

fn poisoned() -> PyErr {
    PyRuntimeError::new_err("wake.state.poisoned")
}

fn samples(bytes: &[u8]) -> PyResult<Vec<i16>> {
    if bytes.len() % 2 != 0 {
        return Err(PyValueError::new_err("wake.audio.misaligned"));
    }
    if bytes.len() > MAX_PCM_BYTES {
        return Err(PyValueError::new_err("wake.audio.too_large"));
    }
    Ok(bytes
        .chunks_exact(2)
        .map(|c| {
            i16::from_le_bytes([
                c.first().copied().unwrap_or(0),
                c.get(1).copied().unwrap_or(0),
            ])
        })
        .collect())
}

fn pcm_bytes(pcm: &[i16]) -> Vec<u8> {
    pcm.iter().flat_map(|s| s.to_le_bytes()).collect()
}

#[pyfunction]
#[allow(clippy::needless_pass_by_value)]
fn wake_enroll(py: Python<'_>, recordings: Vec<Vec<u8>>) -> PyResult<Bound<'_, PyBytes>> {
    let takes = recordings
        .iter()
        .map(|r| samples(r))
        .collect::<PyResult<Vec<_>>>()?;
    let model = py
        .detach(|| Model::enroll(&takes))
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    Ok(PyBytes::new(py, &model.to_bytes()))
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustWakeword {
    inner: Mutex<Detector>,
}

#[pymethods]
impl RustWakeword {
    #[new]
    #[pyo3(signature = (model, sensitivity=1.0, refractory_ms=1500))]
    fn new(model: &[u8], sensitivity: f32, refractory_ms: u32) -> PyResult<Self> {
        if model.len() > MAX_MODEL_BYTES {
            return Err(PyValueError::new_err("wake.error.model"));
        }
        let model = Model::from_bytes(model).map_err(|e| PyValueError::new_err(e.to_string()))?;
        let detector = Detector::new(
            model,
            Config {
                sensitivity,
                refractory_ms,
            },
        )
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok(Self {
            inner: Mutex::new(detector),
        })
    }

    fn push<'py>(
        &self,
        py: Python<'py>,
        audio: &[u8],
    ) -> PyResult<Vec<(f32, f32, Bound<'py, PyBytes>)>> {
        let pcm = samples(audio)?;
        let hits = {
            let mut guard = self.inner.lock().map_err(|_| poisoned())?;
            guard.push(&pcm)
        };
        Ok(hits
            .into_iter()
            .map(|d| {
                (
                    d.confidence,
                    d.distance,
                    PyBytes::new(py, &pcm_bytes(&d.pcm)),
                )
            })
            .collect())
    }

    fn reset(&self) -> PyResult<()> {
        self.inner.lock().map_err(|_| poisoned())?.reset();
        Ok(())
    }
}

#[pyfunction]
#[pyo3(signature = (confidence, speaker, score=0.0, require_speaker=true, min_wake=0.3))]
fn wake_decide(
    confidence: f32,
    speaker: &str,
    score: f32,
    require_speaker: bool,
    min_wake: f32,
) -> PyResult<(bool, String, f32)> {
    let who = match speaker {
        "authorized" => Speaker::Authorized { score },
        "unknown" => Speaker::Unknown { score },
        "ambiguous" => Speaker::Ambiguous,
        "unavailable" => Speaker::Unavailable,
        _ => return Err(PyValueError::new_err("wake.speaker.invalid")),
    };
    let decision = decide(
        confidence,
        who,
        Policy {
            min_wake,
            require_speaker,
        },
    );
    let merged = match decision {
        Decision::Accept { confidence, .. } => confidence,
        _ => 0.0,
    };
    Ok((decision.accepted(), decision.code().to_owned(), merged))
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustWakeword>()?;
    m.add_function(wrap_pyfunction!(wake_enroll, m)?)?;
    m.add_function(wrap_pyfunction!(wake_decide, m)?)?;
    Ok(())
}
