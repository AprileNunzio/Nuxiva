use std::sync::Mutex;

use nuxiva_lyrics_core::{LyricLine, MAX_INPUT, SongClock, parse};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use serde_json::{Value, json};

fn lock_error() -> PyErr {
    PyRuntimeError::new_err("lyrics.state.poisoned")
}

fn line_json(line: &LyricLine) -> Value {
    let words: Vec<Value> = line
        .words
        .iter()
        .map(|w| json!({"t": w.t_ms, "text": w.text}))
        .collect();
    if words.is_empty() {
        json!({"t": line.t_ms, "text": line.text})
    } else {
        json!({"t": line.t_ms, "text": line.text, "words": words})
    }
}

#[pyfunction]
pub fn lyrics_parse(py: Python<'_>, raw: &str) -> PyResult<String> {
    if raw.len() > MAX_INPUT.saturating_mul(2) {
        return Err(PyValueError::new_err("lyrics.too_large"));
    }
    let owned = raw.to_owned();
    let lines = py.detach(move || parse(&owned));
    let rows: Vec<Value> = lines.iter().map(line_json).collect();
    serde_json::to_string(&rows).map_err(|_| PyValueError::new_err("lyrics.encode"))
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug, Default)]
pub struct RustSongClock {
    inner: Mutex<SongClock>,
}

#[pymethods]
impl RustSongClock {
    #[new]
    fn new() -> Self {
        Self::default()
    }

    fn observe(&self, wall_ms: i64, pos_ms: i64) -> PyResult<(i64, bool, i64)> {
        let r = self
            .inner
            .lock()
            .map_err(|_| lock_error())?
            .observe(wall_ms, pos_ms);
        Ok((r.origin_ms, r.jumped, r.correction_ms))
    }

    fn origin(&self) -> PyResult<Option<i64>> {
        Ok(self.inner.lock().map_err(|_| lock_error())?.origin())
    }

    fn reset(&self) -> PyResult<()> {
        self.inner.lock().map_err(|_| lock_error())?.reset();
        Ok(())
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustSongClock>()?;
    m.add_function(wrap_pyfunction!(lyrics_parse, m)?)?;
    Ok(())
}
