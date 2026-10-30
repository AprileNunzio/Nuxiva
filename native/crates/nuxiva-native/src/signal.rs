use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict};

type Enhanced<'py> = (Bound<'py, PyBytes>, f64, f64, f64, Bound<'py, PyDict>);

fn invalid(error: nuxiva_audio_dsp::PcmError) -> PyErr {
    PyValueError::new_err(error.to_string())
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustSignalEnhancer {
    inner: nuxiva_audio_dsp::SignalEnhancer,
}

#[pymethods]
impl RustSignalEnhancer {
    #[new]
    #[pyo3(signature = (target_peak_amplitude = 0.85, noise_floor_ratio = 0.08))]
    fn new(target_peak_amplitude: f32, noise_floor_ratio: f32) -> Self {
        Self {
            inner: nuxiva_audio_dsp::SignalEnhancer::new(target_peak_amplitude, noise_floor_ratio),
        }
    }

    fn enhance_pcm16<'py>(&self, py: Python<'py>, pcm_bytes: &[u8]) -> PyResult<Enhanced<'py>> {
        let samples = nuxiva_audio_dsp::pcm::decode_le(pcm_bytes).map_err(invalid)?;
        let unit = nuxiva_audio_dsp::pcm::to_unit_f32(&samples);
        let enhancer = self.inner.clone();
        let result = py.detach(move || enhancer.enhance(&unit));
        let encoded = nuxiva_audio_dsp::pcm::encode_le(&nuxiva_audio_dsp::pcm::from_unit_f32(
            &result.samples,
        ));
        let features = PyDict::new(py);
        if let Some(found) = result.features {
            features.set_item("zero_crossing_rate", found.zero_crossing_rate)?;
            features.set_item("energy", found.energy)?;
            features.set_item("crest_factor", found.crest_factor)?;
            features.set_item("clarity_score", found.clarity_score)?;
        }
        Ok((
            PyBytes::new(py, &encoded),
            result.original_rms,
            result.enhanced_rms,
            result.snr_gain_db,
            features,
        ))
    }
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustVoiceBiomarkers {
    inner: nuxiva_audio_dsp::VoiceBiomarkerAnalyzer,
}

#[pymethods]
impl RustVoiceBiomarkers {
    #[new]
    #[pyo3(signature = (sample_rate = 16_000))]
    fn new(sample_rate: u32) -> Self {
        Self {
            inner: nuxiva_audio_dsp::VoiceBiomarkerAnalyzer::new(sample_rate),
        }
    }

    fn extract_f32<'py>(&self, py: Python<'py>, samples: &[u8]) -> PyResult<Bound<'py, PyDict>> {
        let signal = nuxiva_audio_dsp::pcm::decode_f32_le(samples).map_err(invalid)?;
        let analyzer = self.inner.clone();
        let bio = py.detach(move || analyzer.extract(&signal));
        let out = PyDict::new(py);
        out.set_item("pitch_f0_mean_hz", bio.pitch_f0_mean_hz)?;
        out.set_item("pitch_variability_st", bio.pitch_variability_st)?;
        out.set_item("jitter_percent", bio.jitter_percent)?;
        out.set_item("shimmer_percent", bio.shimmer_percent)?;
        out.set_item("monotone_score", bio.monotone_score)?;
        out.set_item("vocal_energy_rms", bio.vocal_energy_rms)?;
        out.set_item("speech_pause_ratio", bio.speech_pause_ratio)?;
        out.set_item("depressive_vocal_indicator", bio.depressive_vocal_indicator)?;
        Ok(out)
    }
}
