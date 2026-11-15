#![forbid(unsafe_code)]

use std::sync::Arc;
use serde::{Deserialize, Serialize};

use crate::acoustic::{AcousticAnalyzer, AcousticContext};
use crate::fillers::{FillerEngine, ReflexUtterance, TaskDomain};
use crate::language::LanguageIdentifier;
use crate::plasticity::{PlasticityMemory, PredictionResult};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReflexEvaluation {
    pub language: String,
    pub acoustic: AcousticContext,
    pub immediate_utterance: ReflexUtterance,
    pub fast_prediction: Option<PredictionResult>,
    pub should_execute_fast: bool,
    pub latency_us: u64,
}

#[derive(Debug, Clone)]
pub struct ReflexEngine {
    memory: Arc<PlasticityMemory>,
}

impl Default for ReflexEngine {
    fn default() -> Self {
        Self::new()
    }
}

impl ReflexEngine {
    #[must_use]
    pub fn new() -> Self {
        Self {
            memory: Arc::new(PlasticityMemory::new()),
        }
    }

    #[must_use]
    pub fn evaluate(
        &self,
        query: &str,
        vocal_energy_rms: f32,
        pitch_hz: f32,
        hour_of_day: u8,
    ) -> ReflexEvaluation {
        let t0 = std::time::Instant::now();

        // 1. Acoustic & Circadian Evaluation
        let acoustic = AcousticAnalyzer::analyze(vocal_energy_rms, pitch_hz, hour_of_day);

        // 2. Language Detection
        let lang_info = LanguageIdentifier::identify(query);
        let lang = lang_info.lang_code.as_str();

        // 3. Fast Prediction from Plasticity Memory
        let fast_prediction = self.memory.predict(query);
        let (should_fast, domain) = match &fast_prediction {
            Some(pred) if pred.is_guaranteed && pred.intent == "action_direct" => {
                (true, TaskDomain::ActionDirect)
            }
            Some(pred) if pred.intent == "browser_action" => (false, TaskDomain::SearchWeb),
            Some(pred) if pred.intent == "complex_task" => (false, TaskDomain::ThinkingComplex),
            _ => (false, TaskDomain::ThinkingComplex),
        };

        // 4. Immediate Zero-Silence Reflex Utterance
        let immediate_utterance = FillerEngine::select_utterance(
            query,
            lang,
            acoustic.delivery_style,
            domain,
        );

        let latency_us = t0.elapsed().as_micros() as u64;

        ReflexEvaluation {
            language: lang.to_owned(),
            acoustic,
            immediate_utterance,
            fast_prediction,
            should_execute_fast: should_fast,
            latency_us,
        }
    }

    pub fn learn(&self, query: &str, intent: &str, action: &str) -> bool {
        self.memory.reinforce(query, intent, action)
    }

    #[must_use]
    pub fn memory(&self) -> &PlasticityMemory {
        &self.memory
    }
}
