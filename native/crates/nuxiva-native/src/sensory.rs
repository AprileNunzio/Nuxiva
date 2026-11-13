#![allow(clippy::needless_pass_by_value)]

use std::sync::Mutex;

use nuxiva_dialog_core::{IntentGate, MAX_GATE_TEXT};
use nuxiva_ear_core::aec::{EchoCanceller, MAX_BLOCK};
use nuxiva_ear_core::lock::VoiceLock;
use nuxiva_ear_core::{MAX_DIM, MAX_ROWS, VoicePolicy};
use nuxiva_seal_core::Fernet;
use nuxiva_vision_core::{FrameMeta, Policy, PushOutcome, Source, VisualBuffer};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyBytes;

type Observed = (bool, bool, f32, String);
type Stats = (f32, usize, bool, bool, bool);

fn poisoned() -> PyErr {
    PyRuntimeError::new_err("sensory.poisoned")
}

fn floats(bytes: &[u8], limit: usize, code: &'static str) -> PyResult<Vec<f32>> {
    if bytes.len() % 4 != 0 || bytes.len() / 4 > limit {
        return Err(PyValueError::new_err(code));
    }
    Ok(bytes
        .chunks_exact(4)
        .map(|c| {
            f32::from_le_bytes([
                c.first().copied().unwrap_or(0),
                c.get(1).copied().unwrap_or(0),
                c.get(2).copied().unwrap_or(0),
                c.get(3).copied().unwrap_or(0),
            ])
        })
        .collect())
}

fn finite(value: f64, lo: f64, hi: f64, fallback: f64) -> f64 {
    if value.is_finite() {
        value.clamp(lo, hi)
    } else {
        fallback
    }
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustEchoCanceller {
    inner: Mutex<EchoCanceller>,
}

#[pymethods]
impl RustEchoCanceller {
    #[new]
    fn new() -> Self {
        Self {
            inner: Mutex::new(EchoCanceller::new()),
        }
    }

    fn process<'py>(
        &self,
        py: Python<'py>,
        near: &[u8],
        far: &[u8],
    ) -> PyResult<Bound<'py, PyBytes>> {
        let near = floats(near, MAX_BLOCK, "ear.aec.block")?;
        let far = floats(far, MAX_BLOCK, "ear.aec.block")?;
        let out = py
            .detach(|| {
                self.inner
                    .lock()
                    .ok()
                    .map(|mut aec| aec.process(&near, &far))
            })
            .ok_or_else(poisoned)?
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        let raw: Vec<u8> = out.iter().flat_map(|v| v.to_le_bytes()).collect();
        Ok(PyBytes::new(py, &raw))
    }

    fn stats(&self) -> PyResult<Stats> {
        let s = self.inner.lock().map_err(|_| poisoned())?.stats();
        Ok((s.erle_db, s.delay, s.converged, s.double_talk, s.far_active))
    }

    fn reset(&self) -> PyResult<()> {
        self.inner.lock().map_err(|_| poisoned())?.reset();
        Ok(())
    }
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustVoiceLock {
    inner: Mutex<VoiceLock>,
}

#[pymethods]
impl RustVoiceLock {
    #[new]
    #[pyo3(signature = (hangover=8.0))]
    fn new(hangover: f64) -> Self {
        Self {
            inner: Mutex::new(VoiceLock::new(
                VoicePolicy::default(),
                finite(hangover, 0.5, 120.0, 8.0),
            )),
        }
    }

    fn enrolled(&self) -> PyResult<bool> {
        Ok(self.inner.lock().map_err(|_| poisoned())?.enrolled())
    }

    fn enroll(&self, slug: &str, rows: Vec<Vec<f32>>, consent: bool) -> PyResult<()> {
        if rows.len() > MAX_ROWS || rows.iter().any(|r| r.len() > MAX_DIM) {
            return Err(PyValueError::new_err("ear.lock.rows"));
        }
        self.inner
            .lock()
            .map_err(|_| poisoned())?
            .enroll(slug, &rows, consent)
            .map_err(|e| PyValueError::new_err(e.code()))
    }

    fn revoke(&self) -> PyResult<()> {
        self.inner.lock().map_err(|_| poisoned())?.revoke();
        Ok(())
    }

    fn unlocked(&self, now: f64) -> PyResult<bool> {
        Ok(self.inner.lock().map_err(|_| poisoned())?.unlocked(now))
    }

    fn observe(&self, probe: Vec<f32>, now: f64) -> PyResult<Observed> {
        if probe.len() > MAX_DIM {
            return Err(PyValueError::new_err("ear.lock.rows"));
        }
        let d = self
            .inner
            .lock()
            .map_err(|_| poisoned())?
            .observe(&probe, finite(now, 0.0, f64::MAX, 0.0));
        Ok((d.admit, d.unlocked, d.score, d.reason.to_owned()))
    }

    fn seal<'py>(&self, py: Python<'py>, key: &[u8], now: i64) -> PyResult<Bound<'py, PyBytes>> {
        let fernet = Fernet::new(key).map_err(|e| PyValueError::new_err(e.code()))?;
        let token = self
            .inner
            .lock()
            .map_err(|_| poisoned())?
            .seal(&fernet, now)
            .map_err(|e| PyValueError::new_err(e.code()))?;
        Ok(PyBytes::new(py, token.as_bytes()))
    }

    fn unseal(&self, key: &[u8], token: &[u8], now: i64, consent: bool) -> PyResult<()> {
        let fernet = Fernet::new(key).map_err(|e| PyValueError::new_err(e.code()))?;
        let token =
            std::str::from_utf8(token).map_err(|_| PyValueError::new_err("ear.lock.format"))?;
        self.inner
            .lock()
            .map_err(|_| poisoned())?
            .unseal(&fernet, token, now, consent)
            .map_err(|e| PyValueError::new_err(e.code()))
    }
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustIntentGate {
    inner: IntentGate,
}

#[pymethods]
impl RustIntentGate {
    #[new]
    fn new() -> Self {
        Self {
            inner: IntentGate::new(),
        }
    }

    #[pyo3(signature = (text, named=false))]
    fn judge(
        &self,
        py: Python<'_>,
        text: &str,
        named: bool,
    ) -> PyResult<(String, f32, bool, String)> {
        if text.len() > MAX_GATE_TEXT.saturating_mul(4) {
            return Err(PyValueError::new_err("dialog.gate.too_large"));
        }
        let text = text.to_owned();
        let v = py.detach(|| self.inner.judge(&text, named));
        Ok((
            v.intent.code().to_owned(),
            v.confidence,
            v.drop,
            v.reason.to_owned(),
        ))
    }
}

fn source(code: &str) -> PyResult<Source> {
    match code {
        "screen" => Ok(Source::Screen),
        "webcam" => Ok(Source::Webcam),
        _ => Err(PyValueError::new_err("vision.source")),
    }
}

fn source_code(s: Source) -> &'static str {
    match s {
        Source::Screen => "screen",
        Source::Webcam => "webcam",
    }
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustVisualBuffer {
    inner: Mutex<VisualBuffer>,
}

#[pymethods]
impl RustVisualBuffer {
    #[new]
    #[pyo3(signature = (consent=false, interval_ms=2000, ttl_ms=300_000, capacity=256))]
    fn new(consent: bool, interval_ms: u64, ttl_ms: u64, capacity: usize) -> Self {
        Self {
            inner: Mutex::new(VisualBuffer::new(Policy::new(
                consent,
                interval_ms,
                ttl_ms,
                capacity,
            ))),
        }
    }

    fn set_policy(
        &self,
        consent: bool,
        interval_ms: u64,
        ttl_ms: u64,
        capacity: usize,
    ) -> PyResult<()> {
        self.inner
            .lock()
            .map_err(|_| poisoned())?
            .set_policy(Policy::new(consent, interval_ms, ttl_ms, capacity));
        Ok(())
    }

    fn push(
        &self,
        source_code: &str,
        app: &str,
        title: &str,
        at_ms: u64,
        embedding: Vec<f32>,
    ) -> PyResult<String> {
        let meta = FrameMeta {
            source: source(source_code)?,
            app: app.to_owned(),
            title: title.to_owned(),
            at_ms,
        };
        let outcome = self
            .inner
            .lock()
            .map_err(|_| poisoned())?
            .push(&meta, &embedding);
        Ok(match outcome {
            PushOutcome::Stored => "stored".to_owned(),
            PushOutcome::Rejected(r) => r.code().to_owned(),
        })
    }

    fn query(
        &self,
        probe: Vec<f32>,
        now_ms: u64,
        k: usize,
    ) -> PyResult<Vec<(String, String, u64, f32)>> {
        let hits = self
            .inner
            .lock()
            .map_err(|_| poisoned())?
            .query(&probe, now_ms, k);
        Ok(hits
            .into_iter()
            .map(|h| (h.app, source_code(h.source).to_owned(), h.at_ms, h.score))
            .collect())
    }

    fn context(&self, now_ms: u64) -> PyResult<Option<Vec<f32>>> {
        Ok(self.inner.lock().map_err(|_| poisoned())?.context(now_ms))
    }

    fn current_app(&self, now_ms: u64) -> PyResult<Option<String>> {
        Ok(self
            .inner
            .lock()
            .map_err(|_| poisoned())?
            .current_app(now_ms)
            .map(str::to_owned))
    }

    fn indicator(&self, now_ms: u64) -> PyResult<(bool, Option<String>, usize, Option<u64>)> {
        let i = self.inner.lock().map_err(|_| poisoned())?.indicator(now_ms);
        Ok((
            i.active,
            i.source.map(|s| source_code(s).to_owned()),
            i.frames,
            i.last_ms,
        ))
    }

    fn expire(&self, now_ms: u64) -> PyResult<()> {
        self.inner.lock().map_err(|_| poisoned())?.expire(now_ms);
        Ok(())
    }

    fn wipe(&self) -> PyResult<()> {
        self.inner.lock().map_err(|_| poisoned())?.wipe();
        Ok(())
    }

    fn len(&self) -> PyResult<usize> {
        Ok(self.inner.lock().map_err(|_| poisoned())?.len())
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustEchoCanceller>()?;
    m.add_class::<RustVoiceLock>()?;
    m.add_class::<RustIntentGate>()?;
    m.add_class::<RustVisualBuffer>()
}
