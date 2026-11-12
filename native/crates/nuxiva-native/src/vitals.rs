use std::sync::Mutex;

use nuxiva_vitals_core::{
    Seen, Values, Watch, agreed, breath_rate, camera_allowed, heart_rate, pulse::MAX_SAMPLES,
    valid_slug,
};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

const MAX_SEEN: usize = 32;
const MAX_AGREE: usize = 64;

type Tick<'py> = (Vec<Bound<'py, PyDict>>, Vec<(String, f64)>);

#[pyfunction]
pub fn vitals_parse_ble_heart_rate(frame: &[u8]) -> (Option<f64>, Option<f64>) {
    let sample = nuxiva_vitals_core::parse_heart_rate_measurement(frame);
    (sample.heart_rate_bpm, sample.hrv_rmssd_ms)
}

fn too_long(len: usize) -> PyResult<()> {
    if len > MAX_SAMPLES {
        return Err(PyValueError::new_err("vitals.samples.too_many"));
    }
    Ok(())
}

#[pyfunction]
#[allow(clippy::needless_pass_by_value)]
pub fn vitals_heart_rate(py: Python<'_>, ts: Vec<f64>, rgb: Vec<[f64; 3]>) -> PyResult<(f64, f64)> {
    too_long(ts.len().max(rgb.len()))?;
    let estimate = py.detach(|| heart_rate(&ts, &rgb));
    Ok((estimate.per_minute, estimate.quality))
}

#[pyfunction]
#[allow(clippy::needless_pass_by_value)]
pub fn vitals_breath_rate(py: Python<'_>, ts: Vec<f64>, shift: Vec<f64>) -> PyResult<(f64, f64)> {
    too_long(ts.len().max(shift.len()))?;
    let estimate = py.detach(|| breath_rate(&ts, &shift));
    Ok((estimate.per_minute, estimate.quality))
}

#[pyfunction]
#[allow(clippy::needless_pass_by_value)]
pub fn vitals_agreed(seen: Vec<Option<f64>>, window: usize, spread: f64) -> PyResult<Option<i64>> {
    if seen.len() > MAX_AGREE || window > MAX_AGREE {
        return Err(PyValueError::new_err("vitals.agree.too_many"));
    }
    Ok(agreed(&seen, window, spread))
}

#[pyfunction]
#[pyo3(signature = (consent=None, camera_vitals=None, role="", share_health=None))]
pub fn vitals_camera_allowed(
    consent: Option<bool>,
    camera_vitals: Option<bool>,
    role: &str,
    share_health: Option<bool>,
) -> bool {
    camera_allowed(consent, camera_vitals, role, share_health)
}

fn number(d: &Bound<'_, PyDict>, key: &str) -> PyResult<Option<f64>> {
    match d.get_item(key)? {
        Some(v) if !v.is_none() && !v.is_instance_of::<pyo3::types::PyBool>() => {
            Ok(v.extract::<f64>().ok())
        }
        _ => Ok(None),
    }
}

fn values(item: &Bound<'_, PyDict>, key: &str) -> PyResult<Values> {
    match item.get_item(key)? {
        Some(v) => match v.cast::<PyDict>() {
            Ok(d) => Ok(Values::cleaned(
                number(d, "heart_rate")?,
                number(d, "resp_rate")?,
            )),
            Err(_) => Ok(Values::default()),
        },
        None => Ok(Values::default()),
    }
}

fn seen_of(items: &Bound<'_, PyList>) -> PyResult<Vec<Seen>> {
    let mut out = Vec::with_capacity(items.len().min(MAX_SEEN));
    for item in items.iter().take(MAX_SEEN) {
        let Ok(d) = item.cast::<PyDict>() else {
            continue;
        };
        let Some(slug) = d.get_item("slug")?.and_then(|v| v.extract::<String>().ok()) else {
            continue;
        };
        if valid_slug(&slug) {
            out.push(Seen {
                slug,
                device: values(d, "device")?,
                camera: values(d, "camera")?,
            });
        }
    }
    Ok(out)
}

fn lock_error() -> PyErr {
    PyRuntimeError::new_err("vitals.watch.poisoned")
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug, Default)]
pub struct RustVitalWatch {
    inner: Mutex<Watch>,
}

#[pymethods]
impl RustVitalWatch {
    #[new]
    fn new() -> Self {
        Self::default()
    }

    fn tick<'py>(
        &self,
        py: Python<'py>,
        seen: &Bound<'py, PyList>,
        camera_on: bool,
        now: f64,
    ) -> PyResult<Tick<'py>> {
        let parsed = seen_of(seen)?;
        let outcome = self
            .inner
            .lock()
            .map_err(|_| lock_error())?
            .tick(&parsed, camera_on, now);
        let mut shown = Vec::with_capacity(outcome.shown.len());
        for row in &outcome.shown {
            let d = PyDict::new(py);
            let v = PyDict::new(py);
            if let Some(h) = row.values.heart {
                v.set_item("heart_rate", h)?;
            }
            if let Some(b) = row.values.breath {
                v.set_item("resp_rate", b)?;
            }
            d.set_item("slug", &row.slug)?;
            d.set_item("values", v)?;
            d.set_item("source", row.source.code())?;
            d.set_item("at", (row.at * 10.0).round() / 10.0)?;
            shown.push(d);
        }
        Ok((shown, outcome.force))
    }

    fn forget(&self, slug: &str) -> PyResult<bool> {
        Ok(self.inner.lock().map_err(|_| lock_error())?.forget(slug))
    }

    fn tracked(&self) -> PyResult<usize> {
        Ok(self.inner.lock().map_err(|_| lock_error())?.tracked())
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(vitals_parse_ble_heart_rate, m)?)?;
    m.add_function(wrap_pyfunction!(vitals_heart_rate, m)?)?;
    m.add_function(wrap_pyfunction!(vitals_breath_rate, m)?)?;
    m.add_function(wrap_pyfunction!(vitals_agreed, m)?)?;
    m.add_function(wrap_pyfunction!(vitals_camera_allowed, m)?)?;
    m.add_class::<RustVitalWatch>()?;
    Ok(())
}
