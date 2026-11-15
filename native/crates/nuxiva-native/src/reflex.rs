#![forbid(unsafe_code)]

use nuxiva_reflex_core::{
    BargeResolution, DeliveryStyle, GazeInput, ReflexEngine, SentinelSensorySnapshot,
    VocalStreamPhase,
};
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
        dict.set_item("semantic_token", eval.immediate_utterance.semantic_token)?;
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

        if let Some(oracle) = eval.formal_oracle {
            dict.set_item("has_formal_oracle", true)?;
            dict.set_item("formal_formatted_value", oracle.formatted_value)?;
            dict.set_item("formal_domain", oracle.domain)?;
            dict.set_item("formal_numeric_value", oracle.numeric_value)?;
            dict.set_item(
                "certified_zero_hallucination",
                oracle.certified_zero_hallucination,
            )?;
        } else {
            dict.set_item("has_formal_oracle", false)?;
            dict.set_item("formal_formatted_value", py.None())?;
            dict.set_item("formal_domain", py.None())?;
            dict.set_item("formal_numeric_value", py.None())?;
            dict.set_item("certified_zero_hallucination", false)?;
        }

        Ok(dict)
    }

    pub fn register_lexicon_template(&self, lang: &str, domain: &str, style: &str, template: &str) {
        self.inner
            .register_lexicon_template(lang, domain, style, template);
    }

    // Fase 1: Duplex Barge-In
    #[pyo3(signature = (incoming_utterance, *, now_ms=0))]
    fn barge_in<'py>(
        &self,
        py: Python<'py>,
        incoming_utterance: &str,
        now_ms: u64,
    ) -> PyResult<Bound<'py, PyDict>> {
        let resolution = self.inner.barge_in(incoming_utterance, now_ms);
        let dict = PyDict::new(py);

        match resolution {
            BargeResolution::IgnoredNoise => {
                dict.set_item("action", "ignored")?;
            }
            BargeResolution::ImmediateAbort => {
                dict.set_item("action", "abort")?;
            }
            BargeResolution::AcknowledgedInterruption {
                semantic_token,
                previous_text,
            } => {
                dict.set_item("action", "steer")?;
                dict.set_item("semantic_token", semantic_token)?;
                dict.set_item("previous_text", previous_text)?;
            }
        }

        Ok(dict)
    }

    #[pyo3(signature = (text, *, is_filler=true, now_ms=0))]
    fn start_speaking(&self, text: &str, is_filler: bool, now_ms: u64) {
        let phase = if is_filler {
            VocalStreamPhase::EmittingFiller
        } else {
            VocalStreamPhase::SpeakingReply
        };
        self.inner.start_speaking(text, phase, now_ms);
    }

    fn finish_speaking(&self) {
        self.inner.finish_speaking();
    }

    // Fase 2: Gaze Gate
    #[pyo3(signature = (gaze_score, *, face_detected=true, distance_meters=1.5, voice_proximity=0.2))]
    fn gaze_gate<'py>(
        &self,
        py: Python<'py>,
        gaze_score: f32,
        face_detected: bool,
        distance_meters: f32,
        voice_proximity: f32,
    ) -> PyResult<Bound<'py, PyDict>> {
        let decision = self.inner.gaze_gate(GazeInput {
            gaze_score,
            face_detected,
            distance_meters,
            voice_proximity,
        });

        let dict = PyDict::new(py);
        dict.set_item("is_activated", decision.is_activated)?;
        dict.set_item("requires_wakeword", decision.requires_wakeword)?;
        dict.set_item("engagement_score", decision.engagement_score)?;
        dict.set_item("reason", decision.reason)?;
        Ok(dict)
    }

    // Fase 3: Formal Oracle
    fn formal_resolve<'py>(
        &self,
        py: Python<'py>,
        query: &str,
    ) -> PyResult<Option<Bound<'py, PyDict>>> {
        if let Some(oracle) = self.inner.formal_resolve(query) {
            let dict = PyDict::new(py);
            dict.set_item("formatted_value", oracle.formatted_value)?;
            dict.set_item("domain", oracle.domain)?;
            dict.set_item("numeric_value", oracle.numeric_value)?;
            dict.set_item("confidence", oracle.confidence)?;
            dict.set_item(
                "certified_zero_hallucination",
                oracle.certified_zero_hallucination,
            )?;
            Ok(Some(dict))
        } else {
            Ok(None)
        }
    }

    // Fase 4: Proactive Sentinel
    #[allow(clippy::too_many_arguments)]
    #[pyo3(signature = (cpu_temp_celsius, ram_pressure_ratio, threats_blocked, session_hours, hour_of_day, *, now_ms=0))]
    fn proactive_inspect<'py>(
        &self,
        py: Python<'py>,
        cpu_temp_celsius: f32,
        ram_pressure_ratio: f32,
        threats_blocked: u32,
        session_hours: f32,
        hour_of_day: u8,
        now_ms: u64,
    ) -> PyResult<Bound<'py, PyDict>> {
        let advice = self.inner.proactive_inspect(
            SentinelSensorySnapshot {
                cpu_temp_celsius,
                ram_pressure_ratio,
                network_threats_blocked: threats_blocked,
                continuous_session_hours: session_hours,
                hour_of_day,
            },
            now_ms,
        );

        let dict = PyDict::new(py);
        dict.set_item("should_intervene", advice.should_intervene)?;
        dict.set_item("urgency", format!("{:?}", advice.urgency).to_lowercase())?;
        dict.set_item("semantic_reason", advice.semantic_reason)?;
        dict.set_item("telemetry_metric", advice.telemetry_metric)?;
        dict.set_item("measured_value", advice.measured_value)?;
        dict.set_item("suggested_action", advice.suggested_action)?;
        Ok(dict)
    }

    fn learn(&self, query: &str, intent: &str, action: &str) -> bool {
        self.inner.learn(query, intent, action)
    }
}
