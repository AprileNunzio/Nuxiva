#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};
use std::sync::{Arc, RwLock};

use crate::acoustic::{AcousticAnalyzer, AcousticContext};
use crate::duplex_barge::{BargeResolution, DuplexBargeRouter, VocalStreamPhase};
use crate::fillers::{FillerEngine, LexiconCatalog, ReflexUtterance, TaskDomain};
use crate::formal_oracle::{FormalOracle, FormalOracleResult};
use crate::gaze_gate::{GazeAcousticGate, GazeGateDecision, GazeInput};
use crate::language::LanguageIdentifier;
use crate::plasticity::{PlasticityMemory, PredictionResult};
use crate::proactive_sentinel::{ProactiveAdvice, ProactiveSentinel, SentinelSensorySnapshot};
use crate::shortcut_compiler::{CompiledShortcut, ShortcutCompiler};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReflexEvaluation {
    pub language: String,
    pub acoustic: AcousticContext,
    pub immediate_utterance: ReflexUtterance,
    pub fast_prediction: Option<PredictionResult>,
    pub formal_oracle: Option<FormalOracleResult>,
    pub should_execute_fast: bool,
    pub latency_us: u64,
}

#[derive(Debug, Clone)]
pub struct ReflexEngine {
    memory: Arc<PlasticityMemory>,
    duplex: Arc<RwLock<DuplexBargeRouter>>,
    sentinel: Arc<ProactiveSentinel>,
    fillers: Arc<FillerEngine>,
    compiler: Arc<ShortcutCompiler>,
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
            duplex: Arc::new(RwLock::new(DuplexBargeRouter::new())),
            sentinel: Arc::new(ProactiveSentinel::default()),
            fillers: Arc::new(FillerEngine::new()),
            compiler: Arc::new(ShortcutCompiler::new()),
        }
    }

    pub fn load_lexicon_catalog(&self, catalog: LexiconCatalog) {
        self.fillers.load_catalog(catalog);
    }

    pub fn register_lexicon_template(&self, lang: &str, domain: &str, style: &str, template: &str) {
        self.fillers
            .register_template(lang, domain, style, template);
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

        // 3. Fase 3: Formal Oracle Evaluation (Certified Zero-Hallucination)
        let formal_oracle = FormalOracle::try_resolve(query);

        // 4. Fast Prediction from Plasticity Memory
        let fast_prediction = self.memory.predict(query);

        let (should_fast, domain) = if let Some(ref oracle) = formal_oracle {
            if oracle.resolved {
                (true, TaskDomain::ActionDirect)
            } else {
                (false, TaskDomain::ThinkingComplex)
            }
        } else {
            match &fast_prediction {
                Some(pred) if pred.is_guaranteed && pred.intent == "action_direct" => {
                    (true, TaskDomain::ActionDirect)
                }
                Some(pred) if pred.intent == "browser_action" => (false, TaskDomain::SearchWeb),
                Some(pred) if pred.intent == "complex_task" => (false, TaskDomain::ThinkingComplex),
                _ => (false, TaskDomain::ThinkingComplex),
            }
        };

        let immediate_utterance = if let Some(ref oracle) = formal_oracle {
            ReflexUtterance {
                text: oracle.formatted_value.clone(),
                language: lang.to_owned(),
                delivery_style: acoustic.delivery_style,
                volume_scale: acoustic.volume_scale,
                semantic_token: format!("oracle_{}", oracle.domain),
            }
        } else if let Some(pred) = &fast_prediction
            && should_fast
            && let Some(compiled_text) = self.compiler.resolve_compiled_output(&pred.action)
        {
            ReflexUtterance {
                text: compiled_text,
                language: lang.to_owned(),
                delivery_style: acoustic.delivery_style,
                volume_scale: acoustic.volume_scale,
                semantic_token: format!("shortcut_{}", pred.action),
            }
        } else {
            self.fillers
                .select_utterance(query, lang, acoustic.delivery_style, domain)
        };

        let latency_us = u64::try_from(t0.elapsed().as_micros()).unwrap_or(u64::MAX);

        ReflexEvaluation {
            language: lang.to_owned(),
            acoustic,
            immediate_utterance,
            fast_prediction,
            formal_oracle,
            should_execute_fast: should_fast,
            latency_us,
        }
    }

    pub fn start_speaking(&self, text: &str, phase: VocalStreamPhase, now_ms: u64) {
        if let Ok(mut guard) = self.duplex.write() {
            guard.start_speaking(text, phase, now_ms);
        }
    }

    pub fn finish_speaking(&self) {
        if let Ok(mut guard) = self.duplex.write() {
            guard.finish_speaking();
        }
    }

    #[must_use]
    pub fn barge_in(&self, incoming_utterance: &str, now_ms: u64) -> BargeResolution {
        if let Ok(mut guard) = self.duplex.write() {
            guard.handle_barge_in(incoming_utterance, now_ms)
        } else {
            BargeResolution::IgnoredNoise
        }
    }

    #[must_use]
    pub fn gaze_gate(&self, input: GazeInput) -> GazeGateDecision {
        GazeAcousticGate::evaluate(input)
    }

    #[must_use]
    pub fn formal_resolve(&self, query: &str) -> Option<FormalOracleResult> {
        FormalOracle::try_resolve(query)
    }

    #[must_use]
    pub fn proactive_inspect(
        &self,
        snapshot: SentinelSensorySnapshot,
        now_ms: u64,
    ) -> ProactiveAdvice {
        self.sentinel.inspect(snapshot, now_ms)
    }

    #[must_use]
    pub fn learn(&self, query: &str, intent: &str, action: &str) -> bool {
        self.memory.reinforce(query, intent, action)
    }

    #[must_use]
    pub fn distill_slow_path(
        &self,
        query: &str,
        intent: &str,
        action_target: &str,
        deterministic_output: Option<&str>,
    ) -> Option<CompiledShortcut> {
        let shortcut = self.compiler.record_slow_resolution(
            query,
            intent,
            action_target,
            deterministic_output,
        )?;
        for ex in &shortcut.exemplars {
            let _ = self
                .memory
                .reinforce(ex, &shortcut.intent, &shortcut.action_target);
        }
        Some(shortcut)
    }

    #[must_use]
    pub fn memory(&self) -> &PlasticityMemory {
        &self.memory
    }

    #[must_use]
    pub fn compiler(&self) -> &ShortcutCompiler {
        &self.compiler
    }
}
