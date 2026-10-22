use crate::errors::poisoned;
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use std::sync::{Arc, RwLock};

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
        let media_state: nuxiva_audio_dsp::MediaPlaybackState =
            if media_state_json.trim().is_empty() {
                nuxiva_audio_dsp::MediaPlaybackState::default()
            } else {
                serde_json::from_str(media_state_json)
                    .map_err(|e| PyValueError::new_err(e.to_string()))?
            };

        let num_samples = pcm_bytes.len().saturating_div(2);
        let mut raw_pcm = Vec::with_capacity(num_samples);
        for chunk in pcm_bytes.chunks_exact(2) {
            let b0 = chunk.first().copied().unwrap_or(0);
            let b1 = chunk.get(1).copied().unwrap_or(0);
            raw_pcm.push(i16::from_le_bytes([b0, b1]));
        }

        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        let result = guard.process_frame(&raw_pcm, &media_state);
        serde_json::to_string(&result).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    #[allow(clippy::unused_self)]
    fn compute_rms(&self, pcm_bytes: &[u8]) -> f32 {
        let mut raw_pcm = Vec::with_capacity(pcm_bytes.len().saturating_div(2));
        for chunk in pcm_bytes.chunks_exact(2) {
            let b0 = chunk.first().copied().unwrap_or(0);
            let b1 = chunk.get(1).copied().unwrap_or(0);
            raw_pcm.push(i16::from_le_bytes([b0, b1]));
        }
        nuxiva_audio_dsp::SpectralEntropyVad::compute_rms(&raw_pcm)
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
