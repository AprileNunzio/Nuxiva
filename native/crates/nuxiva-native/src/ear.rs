use std::sync::Mutex;

use nuxiva_ear_core::{
    BINS, Denoiser, DenoiserConfig, MAX_STREAM_SAMPLES, MAX_UTTERANCE_SAMPLES, NoiseTracker,
    clean_utterance, normalize, utterance_gain,
};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyBytes;

const PCM_MAX: f32 = 32_767.0 / 32_768.0;

fn lock_error() -> PyErr {
    PyRuntimeError::new_err("ear.state.poisoned")
}

fn floats(bytes: &[u8], limit: usize) -> PyResult<Vec<f32>> {
    if bytes.len() % 4 != 0 {
        return Err(PyValueError::new_err("ear.audio.misaligned"));
    }
    if bytes.len() / 4 > limit {
        return Err(PyValueError::new_err("ear.audio.too_large"));
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
            if v.is_finite() { v } else { 0.0 }
        })
        .collect())
}

fn float_bytes<'py>(py: Python<'py>, values: &[f32]) -> Bound<'py, PyBytes> {
    let raw: Vec<u8> = values.iter().flat_map(|v| v.to_le_bytes()).collect();
    PyBytes::new(py, &raw)
}

fn pcm_in(bytes: &[u8]) -> PyResult<Vec<f32>> {
    if bytes.len() % 2 != 0 {
        return Err(PyValueError::new_err("Invalid PCM packet"));
    }
    if bytes.len() / 2 > MAX_STREAM_SAMPLES {
        return Err(PyValueError::new_err("ear.audio.too_large"));
    }
    Ok(bytes
        .chunks_exact(2)
        .map(|c| {
            let v = i16::from_le_bytes([
                c.first().copied().unwrap_or(0),
                c.get(1).copied().unwrap_or(0),
            ]);
            f32::from(v) / 32_768.0
        })
        .collect())
}

#[allow(clippy::cast_possible_truncation)]
fn pcm_out(values: &[f32]) -> Vec<u8> {
    values
        .iter()
        .flat_map(|v| {
            let sample = (v.clamp(-1.0, PCM_MAX) * 32_768.0).round() as i16;
            sample.to_le_bytes()
        })
        .collect()
}

fn config(highpass_hz: f32, suppress: bool, floor: f32) -> DenoiserConfig {
    DenoiserConfig {
        highpass_hz,
        suppress,
        floor,
    }
    .sanitized()
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustDenoiser {
    inner: Mutex<Denoiser>,
    config: DenoiserConfig,
}

#[pymethods]
impl RustDenoiser {
    #[new]
    #[pyo3(signature = (highpass_hz=90.0, suppress=true, floor=0.15))]
    fn new(highpass_hz: f32, suppress: bool, floor: f32) -> Self {
        let config = config(highpass_hz, suppress, floor);
        Self {
            inner: Mutex::new(Denoiser::new(config)),
            config,
        }
    }

    #[getter]
    fn enabled(&self) -> bool {
        self.config.enabled()
    }

    #[getter]
    fn suppress(&self) -> bool {
        self.config.suppress
    }

    #[getter]
    fn floor(&self) -> f32 {
        self.config.floor
    }

    #[getter]
    fn highpass_hz(&self) -> f32 {
        self.config.highpass_hz
    }

    fn process<'py>(&self, py: Python<'py>, pcm: &[u8]) -> PyResult<Bound<'py, PyBytes>> {
        if !self.config.enabled() {
            if pcm.len() % 2 != 0 {
                return Err(PyValueError::new_err("Invalid PCM packet"));
            }
            return Ok(PyBytes::new(py, pcm));
        }
        let input = pcm_in(pcm)?;
        let out = py.detach(|| {
            let mut out = Vec::with_capacity(input.len().saturating_add(512));
            self.inner.lock().ok().map(|mut d| {
                d.process(&input, &mut out);
                pcm_out(&out)
            })
        });
        Ok(PyBytes::new(py, &out.ok_or_else(lock_error)?))
    }

    fn process_f32<'py>(&self, py: Python<'py>, audio: &[u8]) -> PyResult<Bound<'py, PyBytes>> {
        let input = floats(audio, MAX_STREAM_SAMPLES)?;
        let out = py.detach(|| {
            let mut out = Vec::with_capacity(input.len().saturating_add(512));
            self.inner.lock().ok().map(|mut d| {
                d.process(&input, &mut out);
                out
            })
        });
        Ok(float_bytes(py, &out.ok_or_else(lock_error)?))
    }

    fn restart(&self) -> PyResult<()> {
        self.inner.lock().map_err(|_| lock_error())?.restart();
        Ok(())
    }

    fn seed(&self, psd: &[u8]) -> PyResult<bool> {
        let values = floats(psd, BINS)?;
        Ok(self.inner.lock().map_err(|_| lock_error())?.seed(&values))
    }

    fn noise<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyBytes>> {
        let guard = self.inner.lock().map_err(|_| lock_error())?;
        Ok(float_bytes(py, guard.noise()))
    }

    fn pending(&self) -> PyResult<usize> {
        Ok(self.inner.lock().map_err(|_| lock_error())?.pending())
    }
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug, Default)]
pub struct RustNoiseTracker {
    inner: Mutex<NoiseTracker>,
}

#[pymethods]
impl RustNoiseTracker {
    #[new]
    fn new() -> Self {
        Self::default()
    }

    fn learn(&self, py: Python<'_>, audio: &[u8]) -> PyResult<()> {
        let input = floats(audio, MAX_STREAM_SAMPLES)?;
        py.detach(|| self.inner.lock().ok().map(|mut t| t.learn(&input)))
            .ok_or_else(lock_error)
    }

    fn psd<'py>(&self, py: Python<'py>) -> PyResult<Option<Bound<'py, PyBytes>>> {
        let guard = self.inner.lock().map_err(|_| lock_error())?;
        Ok(guard.psd().map(|p| float_bytes(py, p)))
    }
}

#[pyfunction]
#[pyo3(signature = (audio, noise=None, highpass_hz=90.0, floor=0.15))]
fn ear_clean_utterance<'py>(
    py: Python<'py>,
    audio: &[u8],
    noise: Option<&[u8]>,
    highpass_hz: f32,
    floor: f32,
) -> PyResult<Bound<'py, PyBytes>> {
    let input = floats(audio, MAX_UTTERANCE_SAMPLES)?;
    let psd = noise.map(|n| floats(n, BINS)).transpose()?;
    let cfg = config(highpass_hz, true, floor);
    let out = py.detach(|| clean_utterance(&input, psd.as_deref(), cfg));
    Ok(float_bytes(py, &out))
}

fn level_args(target: f64, max_gain: f64) -> PyResult<()> {
    if !target.is_finite() || !max_gain.is_finite() || target <= 0.0 || max_gain <= 0.0 {
        return Err(PyValueError::new_err("ear.level.invalid"));
    }
    Ok(())
}

#[pyfunction]
fn ear_normalize<'py>(
    py: Python<'py>,
    audio: &[u8],
    target: f64,
    max_gain: f64,
) -> PyResult<Bound<'py, PyBytes>> {
    level_args(target, max_gain)?;
    let input = floats(audio, MAX_UTTERANCE_SAMPLES)?;
    let out = py.detach(|| normalize(&input, target, max_gain));
    Ok(float_bytes(py, &out))
}

#[pyfunction]
fn ear_utterance_gain(audio: &[u8], target: f64, max_gain: f64) -> PyResult<f64> {
    level_args(target, max_gain)?;
    Ok(utterance_gain(
        &floats(audio, MAX_UTTERANCE_SAMPLES)?,
        target,
        max_gain,
    ))
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustDenoiser>()?;
    m.add_class::<RustNoiseTracker>()?;
    m.add_function(wrap_pyfunction!(ear_clean_utterance, m)?)?;
    m.add_function(wrap_pyfunction!(ear_normalize, m)?)?;
    m.add_function(wrap_pyfunction!(ear_utterance_gain, m)?)?;
    Ok(())
}
