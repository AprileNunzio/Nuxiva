use crate::errors::poisoned;
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict};
use std::sync::{Arc, RwLock};

fn parse_media_state(raw: &str) -> PyResult<nuxiva_audio_dsp::MediaPlaybackState> {
    if raw.trim().is_empty() {
        return Ok(nuxiva_audio_dsp::MediaPlaybackState::default());
    }
    if raw.len() > 4096 {
        return Err(PyValueError::new_err("audio.media_state.too_large"));
    }
    serde_json::from_str(raw).map_err(|e| PyValueError::new_err(e.to_string()))
}

fn decode_pcm(bytes: &[u8]) -> PyResult<Vec<i16>> {
    nuxiva_audio_dsp::pcm::decode_le(bytes).map_err(|e| PyValueError::new_err(e.to_string()))
}

const fn decision_code(decision: nuxiva_audio_dsp::VadDecision) -> &'static str {
    match decision {
        nuxiva_audio_dsp::VadDecision::Silence => "SILENCE",
        nuxiva_audio_dsp::VadDecision::Speech => "SPEECH",
        nuxiva_audio_dsp::VadDecision::MusicOrBackground => "MUSIC_OR_BACKGROUND",
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustAudioCleaner {
    inner: Arc<RwLock<nuxiva_audio_dsp::AudioCleaner>>,
}

#[pymethods]
impl RustAudioCleaner {
    #[new]
    fn new() -> Self {
        Self {
            inner: Arc::new(RwLock::new(nuxiva_audio_dsp::AudioCleaner::new())),
        }
    }

    fn process_pcm_json(&self, pcm_bytes: &[u8], media_state_json: &str) -> PyResult<String> {
        let media_state = parse_media_state(media_state_json)?;
        let raw_pcm = decode_pcm(pcm_bytes)?;
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        let result = guard.process_frame(&raw_pcm, &media_state);
        serde_json::to_string(&result).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    fn process_pcm<'py>(
        &self,
        py: Python<'py>,
        pcm_bytes: &[u8],
        media_state_json: &str,
    ) -> PyResult<Bound<'py, PyDict>> {
        let media_state = parse_media_state(media_state_json)?;
        let raw_pcm = decode_pcm(pcm_bytes)?;
        let frame = {
            let mut guard = self.inner.write().map_err(|_| poisoned())?;
            guard.process_frame(&raw_pcm, &media_state)
        };
        let vad = PyDict::new(py);
        vad.set_item("decision", decision_code(frame.vad.decision))?;
        vad.set_item("speech_confidence", frame.vad.speech_confidence)?;
        vad.set_item("energy_rms", frame.vad.energy_rms)?;
        vad.set_item("is_speech", frame.vad.is_speech)?;
        vad.set_item("reason_code", frame.vad.reason_code.as_str())?;
        let out = PyDict::new(py);
        out.set_item(
            "pcm_clean",
            PyBytes::new(py, &nuxiva_audio_dsp::pcm::encode_le(&frame.pcm_clean)),
        )?;
        out.set_item("vad", vad)?;
        out.set_item("is_gated", frame.is_gated)?;
        out.set_item("attenuation_applied", frame.attenuation_applied)?;
        out.set_item("frame_samples", frame.frame_samples)?;
        Ok(out)
    }

    #[allow(clippy::unused_self)]
    fn compute_rms(&self, pcm_bytes: &[u8]) -> PyResult<f32> {
        let raw_pcm = decode_pcm(pcm_bytes)?;
        Ok(nuxiva_audio_dsp::SpectralEntropyVad::compute_rms(&raw_pcm))
    }

    fn reset(&self) -> PyResult<()> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        guard.reset();
        Ok(())
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug, Default)]
pub struct RustDeviceRouter {
    inner: Arc<RwLock<nuxiva_audio_dsp::FailoverDeviceRouter>>,
}

#[pymethods]
impl RustDeviceRouter {
    #[new]
    fn new(is_proximity: bool) -> Self {
        let mode = if is_proximity {
            nuxiva_audio_dsp::DeviceSelectionMode::MultiMicProximity
        } else {
            nuxiva_audio_dsp::DeviceSelectionMode::HierarchicalFallback
        };
        Self {
            inner: Arc::new(RwLock::new(nuxiva_audio_dsp::FailoverDeviceRouter::new(
                mode,
            ))),
        }
    }

    fn register_device_json(&self, device_json: &str) -> PyResult<()> {
        let device: nuxiva_audio_dsp::AudioDevice =
            serde_json::from_str(device_json).map_err(|e| PyValueError::new_err(e.to_string()))?;
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        guard.register_device(device);
        Ok(())
    }

    fn update_connection_state(&self, device_id: &str, is_connected: bool) -> PyResult<()> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        guard.update_connection_state(device_id, is_connected);
        Ok(())
    }

    fn resolve_active_device_json(&self) -> PyResult<Option<String>> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        let dev = guard.resolve_active_device();
        match dev {
            Some(d) => {
                let serialized =
                    serde_json::to_string(d).map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
                Ok(Some(serialized))
            }
            None => Ok(None),
        }
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug, Default)]
pub struct RustMultiMicTriage {
    inner: Arc<RwLock<nuxiva_audio_dsp::MultiMicTriage>>,
}

#[pymethods]
impl RustMultiMicTriage {
    #[new]
    fn new(hysteresis_margin: f32) -> Self {
        Self {
            inner: Arc::new(RwLock::new(nuxiva_audio_dsp::MultiMicTriage::new(
                hysteresis_margin,
            ))),
        }
    }

    fn elect_best_source_json(&self, reports_json: &str) -> PyResult<Option<String>> {
        let reports: Vec<nuxiva_audio_dsp::SatelliteAudioReport> =
            serde_json::from_str(reports_json).map_err(|e| PyValueError::new_err(e.to_string()))?;
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        Ok(guard.elect_best_source(&reports))
    }

    fn reset(&self) -> PyResult<()> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        guard.reset();
        Ok(())
    }
}
