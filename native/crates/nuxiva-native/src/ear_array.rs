use std::sync::Mutex;

use nuxiva_ear_core::endpoint::{EndpointConfig, Endpointer};
use nuxiva_ear_core::{MAX_ARRAY_FRAME, MAX_CHANNELS, MicArray};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyBytes;

type ArrayTuple<'py> = (Bound<'py, PyBytes>, usize, usize, Vec<f32>);

fn poisoned() -> PyErr {
    PyRuntimeError::new_err("ear.array.poisoned")
}

fn floats(bytes: &[u8]) -> PyResult<Vec<f32>> {
    if bytes.len() % 4 != 0 {
        return Err(PyValueError::new_err("ear.array.misaligned"));
    }
    if bytes.len() / 4 > MAX_ARRAY_FRAME {
        return Err(PyValueError::new_err("ear.array.frame"));
    }
    Ok(bytes
        .chunks_exact(4)
        .map(|c| {
            let v = f32::from_le_bytes([
                c.first().copied().unwrap_or(0),
                c.get(1).copied().unwrap_or(0),
                c.get(2).copied().unwrap_or(0),
                c.get(3).copied().unwrap_or(0),
            ]);
            if v.is_finite() {
                v.clamp(-1.0, 1.0)
            } else {
                0.0
            }
        })
        .collect())
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustMicArray {
    inner: Mutex<MicArray>,
}

#[pymethods]
impl RustMicArray {
    #[new]
    fn new(channels: usize) -> PyResult<Self> {
        if channels > MAX_CHANNELS {
            return Err(PyValueError::new_err("ear.array.channels"));
        }
        let inner = MicArray::new(channels).map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok(Self {
            inner: Mutex::new(inner),
        })
    }

    #[allow(clippy::needless_pass_by_value)]
    fn mix<'py>(&self, py: Python<'py>, frames: Vec<Vec<u8>>) -> PyResult<ArrayTuple<'py>> {
        if frames.len() > MAX_CHANNELS {
            return Err(PyValueError::new_err("ear.array.channels"));
        }
        let decoded = frames
            .iter()
            .map(|f| floats(f))
            .collect::<PyResult<Vec<_>>>()?;
        let result = py.detach(|| {
            let views: Vec<&[f32]> = decoded.iter().map(Vec::as_slice).collect();
            self.inner.lock().ok().map(|mut array| array.mix(&views))
        });
        let frame = result
            .ok_or_else(poisoned)?
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        let raw: Vec<u8> = frame.samples.iter().flat_map(|v| v.to_le_bytes()).collect();
        Ok((
            PyBytes::new(py, &raw),
            frame.best,
            frame.fused,
            frame.scores,
        ))
    }

    fn reset(&self) -> PyResult<()> {
        self.inner.lock().map_err(|_| poisoned())?.reset();
        Ok(())
    }

    #[getter]
    fn channels(&self) -> PyResult<usize> {
        Ok(self.inner.lock().map_err(|_| poisoned())?.channels())
    }
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustEndpointer {
    inner: Mutex<Endpointer>,
}

#[pymethods]
impl RustEndpointer {
    #[new]
    #[pyo3(signature = (end_silence=0.65, wake_hold=1.4, wake_tail=0.45, max_utterance=14.0))]
    fn new(end_silence: f64, wake_hold: f64, wake_tail: f64, max_utterance: f64) -> Self {
        Self {
            inner: Mutex::new(Endpointer::new(EndpointConfig {
                end_silence,
                wake_hold,
                wake_tail,
                max_utterance,
            })),
        }
    }

    fn begin(&self, now: f64) -> PyResult<()> {
        self.inner.lock().map_err(|_| poisoned())?.begin(now);
        Ok(())
    }

    fn wake(&self) -> PyResult<()> {
        self.inner.lock().map_err(|_| poisoned())?.wake();
        Ok(())
    }

    fn reset(&self) -> PyResult<()> {
        self.inner.lock().map_err(|_| poisoned())?.reset();
        Ok(())
    }

    fn frame(&self, now: f64, voiced: bool) -> PyResult<Option<&'static str>> {
        Ok(self
            .inner
            .lock()
            .map_err(|_| poisoned())?
            .frame(now, voiced)
            .map(nuxiva_ear_core::endpoint::EndReason::code))
    }

    #[getter]
    fn holding(&self) -> PyResult<bool> {
        Ok(self.inner.lock().map_err(|_| poisoned())?.holding())
    }

    #[getter]
    fn active(&self) -> PyResult<bool> {
        Ok(self.inner.lock().map_err(|_| poisoned())?.active())
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustMicArray>()?;
    m.add_class::<RustEndpointer>()?;
    Ok(())
}
