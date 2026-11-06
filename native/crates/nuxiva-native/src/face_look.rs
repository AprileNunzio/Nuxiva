use std::sync::Mutex;

use nuxiva_face_core::{Gray, LookError, LookEvent, LookMemory, LookSample, traits};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyDict;

fn look_error(e: LookError) -> PyErr {
    PyValueError::new_err(e.code())
}

fn lock_error() -> PyErr {
    PyRuntimeError::new_err("face.look.poisoned")
}

fn score(sample: &Bound<'_, PyDict>, key: &str) -> PyResult<f32> {
    Ok(match sample.get_item(key)? {
        Some(v) if !v.is_none() => v.extract::<f32>()?,
        _ => 0.0,
    })
}

fn sample_of(sample: &Bound<'_, PyDict>) -> PyResult<LookSample> {
    let hair = match sample.get_item("hair")? {
        Some(v) if !v.is_none() => {
            let text: String = v.extract()?;
            (text.len() <= 16).then_some(text)
        }
        _ => None,
    };
    let samples = match sample.get_item("samples")? {
        Some(v) if !v.is_none() => v.extract::<u32>()?,
        _ => 0,
    };
    Ok(LookSample {
        glasses: score(sample, "glasses")?,
        beard: score(sample, "beard")?,
        fringe: score(sample, "fringe")?,
        cigarette: score(sample, "cigarette")?,
        hair,
        samples,
    })
}

fn event_dict<'py>(py: Python<'py>, e: &LookEvent) -> PyResult<Bound<'py, PyDict>> {
    let d = PyDict::new(py);
    d.set_item("kind", e.kind)?;
    d.set_item("value", &e.value)?;
    d.set_item("previous", e.previous.as_deref())?;
    Ok(d)
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustFaceLook {
    inner: Mutex<LookMemory>,
}

#[pymethods]
impl RustFaceLook {
    #[new]
    #[pyo3(signature = (state=None))]
    fn new(state: Option<&str>) -> PyResult<Self> {
        let memory = LookMemory::from_json(state.unwrap_or_default()).map_err(look_error)?;
        Ok(Self {
            inner: Mutex::new(memory),
        })
    }

    fn update<'py>(
        &self,
        py: Python<'py>,
        sample: &Bound<'py, PyDict>,
        now: f64,
    ) -> PyResult<Vec<Bound<'py, PyDict>>> {
        let parsed = sample_of(sample)?;
        let events = self
            .inner
            .lock()
            .map_err(|_| lock_error())?
            .update(&parsed, now);
        events.iter().map(|e| event_dict(py, e)).collect()
    }

    fn forget(&self, kind: &str) -> PyResult<()> {
        self.inner
            .lock()
            .map_err(|_| lock_error())?
            .forget(kind)
            .map_err(look_error)
    }

    fn state(&self) -> PyResult<String> {
        self.inner
            .lock()
            .map_err(|_| lock_error())?
            .to_json()
            .map_err(look_error)
    }

    fn summary<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let s = self.inner.lock().map_err(|_| lock_error())?.summary();
        let d = PyDict::new(py);
        d.set_item("glasses", s.glasses)?;
        d.set_item("beard", s.beard)?;
        d.set_item("fringe", s.fringe)?;
        d.set_item("hair", s.hair)?;
        d.set_item("smoker", s.smoker)?;
        d.set_item("smoking_episodes", s.smoking_episodes)?;
        d.set_item("observations", s.observations)?;
        Ok(d)
    }
}

#[pyfunction]
fn face_traits<'py>(
    py: Python<'py>,
    gray: &[u8],
    width: usize,
    height: usize,
) -> PyResult<Bound<'py, PyDict>> {
    let image = Gray::new(gray, width, height).map_err(|e| PyValueError::new_err(e.code()))?;
    let t = py.detach(|| traits(&image));
    let d = PyDict::new(py);
    d.set_item("glasses", t.glasses)?;
    d.set_item("beard", t.beard)?;
    d.set_item("fringe", t.fringe)?;
    d.set_item("cigarette", t.cigarette)?;
    Ok(d)
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("FACE_LOOK_KINDS", nuxiva_face_core::KINDS.to_vec())?;
    m.add("FACE_HAIR_COLORS", nuxiva_face_core::HAIR_COLORS.to_vec())?;
    m.add_class::<RustFaceLook>()?;
    m.add_function(wrap_pyfunction!(face_traits, m)?)?;
    Ok(())
}
