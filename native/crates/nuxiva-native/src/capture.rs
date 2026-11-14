use std::sync::Mutex;

use nuxiva_vision_core::{Cadence, Source, Verdict, dhash};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;

fn poisoned() -> PyErr {
    PyRuntimeError::new_err("capture.poisoned")
}

fn lane(code: &str) -> PyResult<Source> {
    match code {
        "screen" => Ok(Source::Screen),
        "webcam" => Ok(Source::Webcam),
        _ => Err(PyValueError::new_err("capture.source")),
    }
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustCadence {
    inner: Mutex<Cadence>,
}

#[pymethods]
impl RustCadence {
    #[new]
    #[pyo3(signature = (base_ms=2000, ceiling_ms=30_000))]
    fn new(base_ms: u64, ceiling_ms: u64) -> Self {
        Self {
            inner: Mutex::new(Cadence::new(base_ms, ceiling_ms)),
        }
    }

    fn due(&self, source: &str, now_ms: u64) -> PyResult<bool> {
        Ok(self
            .inner
            .lock()
            .map_err(|_| poisoned())?
            .due(lane(source)?, now_ms))
    }

    fn interval_ms(&self, source: &str) -> PyResult<u64> {
        Ok(self
            .inner
            .lock()
            .map_err(|_| poisoned())?
            .interval_ms(lane(source)?))
    }

    fn admit(&self, source: &str, thumb: &[u8], now_ms: u64) -> PyResult<String> {
        let hash = dhash(thumb).ok_or_else(|| PyValueError::new_err("capture.thumb"))?;
        let verdict = self
            .inner
            .lock()
            .map_err(|_| poisoned())?
            .admit(lane(source)?, hash, now_ms);
        Ok(match verdict {
            Verdict::Embed => "embed",
            Verdict::NotDue => "not_due",
            Verdict::Unchanged => "unchanged",
        }
        .to_owned())
    }

    fn reset(&self) -> PyResult<()> {
        self.inner.lock().map_err(|_| poisoned())?.reset();
        Ok(())
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustCadence>()
}
