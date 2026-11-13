use std::sync::Mutex;

use nuxiva_ear_core::{AttributionPolicy, Attributor, Evidence, WindowVerdict};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyDict;

const MAX_PROBE: usize = 1024;
const MAX_WINDOWS: usize = 16;

fn lock_error() -> PyErr {
    PyRuntimeError::new_err("attribution.state.poisoned")
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug, Default)]
pub struct RustAttributor {
    inner: Mutex<Attributor>,
}

#[pymethods]
impl RustAttributor {
    #[new]
    #[pyo3(signature = (min_seconds=1.2, strict_bonus=0.05, programme_bonus=0.08, foreign_margin=0.1, window_gap=0.04, clear_gap=0.08))]
    fn new(
        min_seconds: f32,
        strict_bonus: f32,
        programme_bonus: f32,
        foreign_margin: f32,
        window_gap: f32,
        clear_gap: f32,
    ) -> Self {
        Self {
            inner: Mutex::new(Attributor::new(AttributionPolicy {
                min_seconds,
                strict_bonus,
                programme_bonus,
                foreign_margin,
                window_gap,
                clear_gap,
            })),
        }
    }

    fn clear(&self) -> PyResult<()> {
        self.inner.lock().map_err(|_| lock_error())?.clear();
        Ok(())
    }

    fn foreign_count(&self) -> PyResult<usize> {
        Ok(self.inner.lock().map_err(|_| lock_error())?.foreign_count())
    }

    fn foreign_recent(&self, now: f64, within: f64) -> PyResult<usize> {
        Ok(self
            .inner
            .lock()
            .map_err(|_| lock_error())?
            .foreign_recent(now, within))
    }

    #[allow(clippy::needless_pass_by_value, clippy::too_many_arguments)]
    #[pyo3(signature = (probe, slug, score, limit, seconds, programme, windows, now))]
    fn judge<'py>(
        &self,
        py: Python<'py>,
        probe: Vec<f32>,
        slug: Option<String>,
        score: f32,
        limit: f32,
        seconds: f32,
        programme: bool,
        windows: Vec<(Option<String>, f32)>,
        now: f64,
    ) -> PyResult<Bound<'py, PyDict>> {
        if probe.is_empty() || probe.len() > MAX_PROBE || windows.len() > MAX_WINDOWS {
            return Err(PyValueError::new_err("attribution.input.invalid"));
        }
        let windows: Vec<WindowVerdict> = windows
            .into_iter()
            .map(|(slug, score)| WindowVerdict { slug, score })
            .collect();
        let verdict = self
            .inner
            .lock()
            .map_err(|_| lock_error())?
            .judge(&Evidence {
                probe: &probe,
                slug: slug.as_deref(),
                score,
                limit,
                seconds,
                programme,
                windows: &windows,
                now,
            });
        let out = PyDict::new(py);
        out.set_item("slug", verdict.slug)?;
        out.set_item("verified", verdict.verified)?;
        out.set_item("foreign", verdict.foreign)?;
        out.set_item("score", verdict.score)?;
        out.set_item("needed", verdict.needed)?;
        out.set_item("reason", verdict.reason)?;
        Ok(out)
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustAttributor>()
}
