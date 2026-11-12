use std::sync::{Mutex, RwLock};

use nuxiva_ear_core::{MAX_DIM, MAX_ROWS, VoiceBook, VoicePolicy, VoiceTracker, split_turns};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyDict;

const MAX_WINDOWS: usize = 512;

fn lock_error() -> PyErr {
    PyRuntimeError::new_err("voice.state.poisoned")
}

fn check_probe(probe: &[f32]) -> PyResult<()> {
    if probe.is_empty() || probe.len() > MAX_DIM {
        return Err(PyValueError::new_err("voice.probe.invalid"));
    }
    Ok(())
}

fn policy(
    base: f32,
    margin: f32,
    twin_margin: f32,
    twin_similarity: f32,
    adaptive: bool,
) -> VoicePolicy {
    VoicePolicy {
        base,
        margin,
        twin_margin,
        twin_similarity,
        adaptive,
    }
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustVoiceBook {
    inner: RwLock<VoiceBook>,
}

#[pymethods]
impl RustVoiceBook {
    #[new]
    #[pyo3(signature = (base=0.62, margin=0.06, twin_margin=0.12, twin_similarity=0.5, adaptive=true))]
    fn new(base: f32, margin: f32, twin_margin: f32, twin_similarity: f32, adaptive: bool) -> Self {
        Self {
            inner: RwLock::new(VoiceBook::new(policy(
                base,
                margin,
                twin_margin,
                twin_similarity,
                adaptive,
            ))),
        }
    }

    #[pyo3(signature = (base, margin, twin_margin, twin_similarity, adaptive))]
    fn set_policy(
        &self,
        base: f32,
        margin: f32,
        twin_margin: f32,
        twin_similarity: f32,
        adaptive: bool,
    ) -> PyResult<()> {
        self.inner
            .write()
            .map_err(|_| lock_error())?
            .set_policy(policy(base, margin, twin_margin, twin_similarity, adaptive));
        Ok(())
    }

    fn policy(&self) -> PyResult<(f32, f32, f32, f32, bool)> {
        let p = self.inner.read().map_err(|_| lock_error())?.policy();
        Ok((
            p.base,
            p.margin,
            p.twin_margin,
            p.twin_similarity,
            p.adaptive,
        ))
    }

    #[allow(clippy::needless_pass_by_value)]
    fn set_person(&self, slug: &str, rows: Vec<Vec<f32>>) -> PyResult<bool> {
        if rows.len() > MAX_ROWS {
            return Err(PyValueError::new_err("voice.rows.too_many"));
        }
        Ok(self
            .inner
            .write()
            .map_err(|_| lock_error())?
            .set_person(slug, &rows))
    }

    fn remove(&self, slug: &str) -> PyResult<()> {
        self.inner.write().map_err(|_| lock_error())?.remove(slug);
        Ok(())
    }

    fn __len__(&self) -> PyResult<usize> {
        Ok(self.inner.read().map_err(|_| lock_error())?.len())
    }

    fn limit(&self, slug: &str) -> PyResult<Option<f32>> {
        Ok(self.inner.read().map_err(|_| lock_error())?.limit(slug))
    }

    fn twins(&self) -> PyResult<Vec<(String, String)>> {
        Ok(self.inner.read().map_err(|_| lock_error())?.twins())
    }

    #[allow(clippy::needless_pass_by_value)]
    fn scores(&self, probe: Vec<f32>) -> PyResult<Vec<(String, f32)>> {
        check_probe(&probe)?;
        Ok(self.inner.read().map_err(|_| lock_error())?.scores(&probe))
    }

    #[allow(clippy::needless_pass_by_value)]
    fn verdict<'py>(&self, py: Python<'py>, probe: Vec<f32>) -> PyResult<Bound<'py, PyDict>> {
        check_probe(&probe)?;
        let v = self.inner.read().map_err(|_| lock_error())?.verdict(&probe);
        let out = PyDict::new(py);
        out.set_item("slug", v.slug)?;
        out.set_item("best", v.best)?;
        out.set_item("score", v.score)?;
        out.set_item("second", v.second)?;
        out.set_item("second_score", v.second_score)?;
        out.set_item("ambiguous", v.ambiguous)?;
        out.set_item("reason", v.reason)?;
        Ok(out)
    }
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug, Default)]
pub struct RustVoiceTracker {
    inner: Mutex<VoiceTracker>,
}

#[pymethods]
impl RustVoiceTracker {
    #[new]
    fn new() -> Self {
        Self::default()
    }

    #[allow(clippy::needless_pass_by_value)]
    #[pyo3(signature = (probe, now, known=None))]
    fn observe<'py>(
        &self,
        py: Python<'py>,
        probe: Vec<f32>,
        now: f64,
        known: Option<&str>,
    ) -> PyResult<Option<Bound<'py, PyDict>>> {
        check_probe(&probe)?;
        let info = self
            .inner
            .lock()
            .map_err(|_| lock_error())?
            .observe(&probe, now, known);
        let Some(info) = info else {
            return Ok(None);
        };
        let out = PyDict::new(py);
        out.set_item("voice_label", info.label)?;
        out.set_item("voice_known", info.known)?;
        out.set_item("new_voice", info.new_voice)?;
        out.set_item("same_speaker", info.same_as_last)?;
        out.set_item("voices_active", info.active_voices)?;
        out.set_item("voice_similarity", info.similarity)?;
        Ok(Some(out))
    }

    fn active(&self, now: f64) -> PyResult<usize> {
        Ok(self.inner.lock().map_err(|_| lock_error())?.active(now))
    }
}

#[pyfunction]
#[allow(clippy::needless_pass_by_value)]
fn ear_split_turns(windows: Vec<Vec<f32>>, change: f32) -> PyResult<Vec<usize>> {
    if windows.len() > MAX_WINDOWS || windows.iter().any(|w| w.len() > MAX_DIM) {
        return Err(PyValueError::new_err("voice.windows.too_many"));
    }
    Ok(split_turns(&windows, change))
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustVoiceBook>()?;
    m.add_class::<RustVoiceTracker>()?;
    m.add_function(wrap_pyfunction!(ear_split_turns, m)?)?;
    Ok(())
}
