#![forbid(unsafe_code)]

use nuxiva_reflex_core::{DeliveryStyle, ReflexEngine};
use pyo3::prelude::*;
use pyo3::types::PyDict;

#[pyclass(module = "nuxiva_native", skip_from_py_object)]
#[derive(Debug, Clone)]
pub struct RustReflexEngine {
    inner: ReflexEngine,
}

#[pymethods]
impl RustReflexEngine {
    #[new]
    fn new() -> Self {
        Self {
            inner: ReflexEngine::new(),
        }
    }

    #[pyo3(signature = (query, *, vocal_energy_rms=0.15, pitch_hz=140.0, hour_of_day=14))]
    fn evaluate<'py>(
        &self,
        py: Python<'py>,
        query: &str,
        vocal_energy_rms: f32,
        pitch_hz: f32,
        hour_of_day: u8,
    ) -> PyResult<Bound<'py, PyDict>> {
        let eval = self
            .inner
            .evaluate(query, vocal_energy_rms, pitch_hz, hour_of_day);

        let dict = PyDict::new(py);
        dict.set_item("language", eval.language)?;
        dict.set_item("is_whisper", eval.acoustic.is_whisper_detected)?;
        dict.set_item("is_night", eval.acoustic.is_night_time)?;

        let style_str = match eval.acoustic.delivery_style {
            DeliveryStyle::Normal => "normal",
            DeliveryStyle::Whisper => "whisper",
            DeliveryStyle::NightDiscreet => "night_discreet",
        };
        dict.set_item("delivery_style", style_str)?;
        dict.set_item("volume_scale", eval.acoustic.volume_scale)?;
        dict.set_item("immediate_filler", eval.immediate_utterance.text)?;
        dict.set_item("should_execute_fast", eval.should_execute_fast)?;
        dict.set_item("latency_us", eval.latency_us)?;

        if let Some(pred) = eval.fast_prediction {
            dict.set_item("fast_intent", pred.intent)?;
            dict.set_item("fast_action", pred.action)?;
            dict.set_item("fast_confidence", pred.confidence)?;
            dict.set_item("is_guaranteed", pred.is_guaranteed)?;
            dict.set_item("conformal_margin", pred.conformal_margin)?;
        } else {
            dict.set_item("fast_intent", py.None())?;
            dict.set_item("fast_action", py.None())?;
            dict.set_item("fast_confidence", 0.0)?;
            dict.set_item("is_guaranteed", false)?;
            dict.set_item("conformal_margin", 0.0)?;
        }

        Ok(dict)
    }

    fn learn(&self, query: &str, intent: &str, action: &str) -> bool {
        self.inner.learn(query, intent, action)
    }
}
