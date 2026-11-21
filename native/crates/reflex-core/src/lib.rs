#![forbid(unsafe_code)]

pub mod acoustic;
pub mod duplex_barge;
pub mod engine;
pub mod fillers;
pub mod formal_oracle;
pub mod gaze_gate;
pub mod language;
pub mod plasticity;
pub mod proactive_sentinel;
pub mod shortcut_compiler;

pub use acoustic::{AcousticAnalyzer, AcousticContext, DeliveryStyle};
pub use duplex_barge::{BargeResolution, DuplexBargeRouter, VocalStreamPhase, VocalStreamState};
pub use engine::{ReflexEngine, ReflexEvaluation};
pub use fillers::{FillerEngine, LexiconCatalog, ReflexUtterance, TaskDomain};
pub use formal_oracle::{FormalOracle, FormalOracleResult};
pub use gaze_gate::{GazeAcousticGate, GazeGateDecision, GazeInput};
pub use language::{LanguageDetection, LanguageIdentifier};
pub use plasticity::{PlasticityMemory, PredictionResult};
pub use proactive_sentinel::{
    ProactiveAdvice, ProactiveSentinel, ProactiveUrgency, SentinelSensorySnapshot,
};
pub use shortcut_compiler::{CompiledShortcut, ShortcutCompiler, SlowPathTrace};

#[cfg(test)]
#[allow(clippy::expect_used, clippy::panic)]
mod tests {
    use super::*;

    #[test]
    fn test_acoustic_whisper_and_night() {
        let ctx_whisper = AcousticAnalyzer::analyze(0.02, 140.0, 15);
        assert_eq!(ctx_whisper.delivery_style, DeliveryStyle::Whisper);
        assert!(ctx_whisper.volume_scale < 0.5);

        let ctx_night = AcousticAnalyzer::analyze(0.15, 140.0, 23);
        assert_eq!(ctx_night.delivery_style, DeliveryStyle::NightDiscreet);
        assert!(ctx_night.volume_scale <= 0.6);

        let ctx_day = AcousticAnalyzer::analyze(0.15, 140.0, 14);
        assert_eq!(ctx_day.delivery_style, DeliveryStyle::Normal);
        assert_eq!(ctx_day.volume_scale, 1.0);
    }

    #[test]
    fn test_pure_lexicon_catalog_resolution() {
        let engine = ReflexEngine::new();

        // Register custom templates dynamically at runtime (zero code hardcoding)
        engine.register_lexicon_template(
            "it",
            "thinking",
            "normal",
            "Sto elaborando la soluzione...",
        );
        engine.register_lexicon_template("ja", "thinking", "normal", "少々お待ちください...");

        let out_it = engine.evaluate(
            "Spiegami per favore come funziona la fisica quantistica",
            0.15,
            140.0,
            14,
        );
        assert_eq!(out_it.language, "it");
        assert_eq!(
            out_it.immediate_utterance.text,
            "Sto elaborando la soluzione..."
        );

        let out_ja = engine.evaluate("量子力学を説明してください", 0.15, 140.0, 14);
        assert_eq!(out_ja.immediate_utterance.text, "少々お待ちください...");
    }

    #[test]
    fn test_self_learning_plasticity() {
        let engine = ReflexEngine::new();

        let query = "attiva modalità relax in camera";
        let eval_before = engine.evaluate(query, 0.15, 140.0, 14);
        assert!(!eval_before.should_execute_fast);

        let learned = engine.learn(query, "action_direct", "home_assistant.scene_relax");
        assert!(learned);

        let eval_after = engine.evaluate(query, 0.15, 140.0, 14);
        let pred = eval_after.fast_prediction.expect("Must have prediction");
        assert_eq!(pred.intent, "action_direct");
        assert_eq!(pred.action, "home_assistant.scene_relax");
        assert!(pred.confidence >= 0.85);
    }

    #[test]
    fn test_fase1_duplex_barge_in() {
        let engine = ReflexEngine::new();
        engine.start_speaking(
            "Caricamento dei dati di telemetria...",
            VocalStreamPhase::EmittingFiller,
            1000,
        );

        // Single word quick abort -> ImmediateAbort
        let res_abort = engine.barge_in("Stop", 1200);
        assert_eq!(res_abort, BargeResolution::ImmediateAbort);

        // Conversational correction -> Steer with semantic token
        engine.start_speaking(
            "Analizzo i parametri...",
            VocalStreamPhase::SpeakingReply,
            2000,
        );
        let res_steer = engine.barge_in("Anzi controlla la rete", 2300);
        match res_steer {
            BargeResolution::AcknowledgedInterruption {
                semantic_token,
                previous_text,
            } => {
                assert_eq!(semantic_token, "conversation.interruption_steer");
                assert_eq!(previous_text, "Analizzo i parametri...");
            }
            _ => panic!("Expected AcknowledgedInterruption"),
        }
    }

    #[test]
    fn test_fase2_gaze_gate_natural_activation() {
        let engine = ReflexEngine::new();

        let direct_input = GazeInput {
            gaze_score: 0.85,
            face_detected: true,
            distance_meters: 1.2,
            voice_proximity: 0.25,
        };
        let decision_direct = engine.gaze_gate(direct_input);
        assert!(decision_direct.is_activated);
        assert!(!decision_direct.requires_wakeword);

        let indirect_input = GazeInput {
            gaze_score: 0.20,
            face_detected: true,
            distance_meters: 2.8,
            voice_proximity: 0.15,
        };
        let decision_indirect = engine.gaze_gate(indirect_input);
        assert!(!decision_indirect.is_activated);
        assert!(decision_indirect.requires_wakeword);
    }

    #[test]
    fn test_fase3_formal_oracle_zero_hallucination() {
        let engine = ReflexEngine::new();

        let math_eval = engine.evaluate("calcola 42 * 128", 0.15, 140.0, 14);
        assert!(math_eval.should_execute_fast);
        let oracle_res = math_eval
            .formal_oracle
            .expect("Must have formal oracle result");
        assert!(oracle_res.certified_zero_hallucination);
        assert_eq!(oracle_res.formatted_value, "5376");

        let hw_eval = engine.evaluate("quanta memoria ram abbiamo?", 0.15, 140.0, 14);
        assert!(hw_eval.should_execute_fast);
        let hw_oracle = hw_eval.formal_oracle.expect("Must have hardware telemetry");
        assert!(hw_oracle.certified_zero_hallucination);
        assert!(hw_oracle.formatted_value.contains("11.4 GB"));
    }

    #[test]
    fn test_fase4_proactive_sentinel_autonomous() {
        let engine = ReflexEngine::new();

        let hot_snapshot = SentinelSensorySnapshot {
            cpu_temp_celsius: 89.0,
            ram_pressure_ratio: 0.80,
            network_threats_blocked: 0,
            continuous_session_hours: 1.0,
            hour_of_day: 15,
        };
        let advice_hot = engine.proactive_inspect(hot_snapshot, 10_000);
        assert!(advice_hot.should_intervene);
        assert_eq!(advice_hot.urgency, ProactiveUrgency::Critical);
        assert_eq!(advice_hot.semantic_reason, "thermal_alert_critical");

        let threat_snapshot = SentinelSensorySnapshot {
            cpu_temp_celsius: 50.0,
            ram_pressure_ratio: 0.40,
            network_threats_blocked: 7,
            continuous_session_hours: 1.0,
            hour_of_day: 16,
        };
        let advice_sec = engine.proactive_inspect(threat_snapshot, 400_000);
        assert!(advice_sec.should_intervene);
        assert_eq!(advice_sec.urgency, ProactiveUrgency::Medium);
        assert_eq!(advice_sec.semantic_reason, "network_threats_mitigated");
    }

    #[test]
    fn test_zero_token_shortcut_distillation() {
        let engine = ReflexEngine::new();
        let q1 = "avvia backup cassaforte crittografata";
        let q2 = "avvia il backup della cassaforte crittografata";
        let q3 = "esegui backup cassaforte crittografata adesso";

        assert!(
            engine
                .distill_slow_path(
                    q1,
                    "action_direct",
                    "vault.backup_encrypted",
                    Some("i18n.vault.backup_done")
                )
                .is_none()
        );
        assert!(
            engine
                .distill_slow_path(
                    q2,
                    "action_direct",
                    "vault.backup_encrypted",
                    Some("i18n.vault.backup_done")
                )
                .is_none()
        );
        let compiled = engine.distill_slow_path(
            q3,
            "action_direct",
            "vault.backup_encrypted",
            Some("i18n.vault.backup_done"),
        );
        assert!(compiled.is_some());
        if let Some(sc) = compiled {
            assert!(sc.promoted_to_fast_path);
            assert_eq!(sc.consolidated_hits, 3);
        }

        let eval = engine.evaluate(q1, 0.15, 140.0, 14);
        assert!(eval.should_execute_fast);
        assert_eq!(eval.immediate_utterance.text, "i18n.vault.backup_done");
    }
}
