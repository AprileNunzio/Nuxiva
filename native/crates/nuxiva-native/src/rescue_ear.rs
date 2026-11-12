use std::sync::Mutex;

use nuxiva_ear_core::danger_sound::{DangerSound, MAX_FEED};
use nuxiva_ear_core::distress::{MAX_TEXT, analyze};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use serde_json::{Value, json};

type SoundTuple = (&'static str, f64, f64, f64, f64);

fn floats(bytes: &[u8]) -> PyResult<Vec<f32>> {
    if bytes.len() % 4 != 0 {
        return Err(PyValueError::new_err("ear.audio.misaligned"));
    }
    if bytes.len() / 4 > MAX_FEED {
        return Err(PyValueError::new_err("ear.audio.too_large"));
    }
    Ok(bytes
        .chunks_exact(4)
        .map(|c| {
            let v = <[u8; 4]>::try_from(c).map_or(0.0, f32::from_le_bytes);
            if v.is_finite() { v } else { 0.0 }
        })
        .collect())
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustDangerSound {
    inner: Mutex<DangerSound>,
}

#[pymethods]
impl RustDangerSound {
    #[new]
    fn new() -> Self {
        Self {
            inner: Mutex::new(DangerSound::new()),
        }
    }

    #[pyo3(signature = (audio, media=false))]
    fn feed(&self, py: Python<'_>, audio: &[u8], media: bool) -> PyResult<Vec<SoundTuple>> {
        let input = floats(audio)?;
        let events = py
            .detach(|| self.inner.lock().ok().map(|mut d| d.feed(&input, media)))
            .ok_or_else(|| PyRuntimeError::new_err("ear.state.poisoned"))?;
        Ok(events
            .into_iter()
            .map(|e| {
                (
                    e.kind.code(),
                    e.probability,
                    e.confidence,
                    e.at_s,
                    e.duration_s,
                )
            })
            .collect())
    }

    fn floor(&self) -> PyResult<f32> {
        Ok(self
            .inner
            .lock()
            .map_err(|_| PyRuntimeError::new_err("ear.state.poisoned"))?
            .floor())
    }
}

#[pyfunction]
#[pyo3(signature = (text, asked=false, media=false, speech_confidence=0.8))]
fn ear_distress(text: &str, asked: bool, media: bool, speech_confidence: f64) -> PyResult<String> {
    if text.len() > MAX_TEXT * 4 {
        return Err(PyValueError::new_err("ear.distress.too_long"));
    }
    let d = analyze(text, asked, media, speech_confidence);
    let detections: Vec<Value> = d
        .detections
        .iter()
        .map(|x| {
            json!({"cue": x.cue.code(), "phrase": x.phrase, "lang": x.lang, "start": x.start,
                   "probability": x.probability, "negated": x.negated})
        })
        .collect();
    serde_json::to_string(&json!({
        "detections": detections,
        "help": d.help,
        "threat": d.threat,
        "fire": d.fire,
        "confidence": d.confidence,
        "answer": d.answer.map(nuxiva_ear_core::distress::Answer::code),
        "lang": d.lang,
    }))
    .map_err(|_| PyRuntimeError::new_err("ear.distress.encode"))
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustDangerSound>()?;
    m.add_function(wrap_pyfunction!(ear_distress, m)?)
}
