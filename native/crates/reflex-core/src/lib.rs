#![forbid(unsafe_code)]

pub mod acoustic;
pub mod engine;
pub mod fillers;
pub mod language;
pub mod plasticity;

pub use acoustic::{AcousticAnalyzer, AcousticContext, DeliveryStyle};
pub use engine::{ReflexEngine, ReflexEvaluation};
pub use fillers::{FillerEngine, ReflexUtterance, TaskDomain};
pub use language::{LanguageDetection, LanguageIdentifier};
pub use plasticity::{PlasticityMemory, PredictionResult};

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_acoustic_whisper_and_night() {
        // Whisper during day
        let ctx_whisper = AcousticAnalyzer::analyze(0.02, 140.0, 15);
        assert_eq!(ctx_whisper.delivery_style, DeliveryStyle::Whisper);
        assert!(ctx_whisper.volume_scale < 0.5);

        // Night time (23:00) with normal energy
        let ctx_night = AcousticAnalyzer::analyze(0.15, 140.0, 23);
        assert_eq!(ctx_night.delivery_style, DeliveryStyle::NightDiscreet);
        assert!(ctx_night.volume_scale <= 0.6);

        // Daytime normal (14:00)
        let ctx_day = AcousticAnalyzer::analyze(0.15, 140.0, 14);
        assert_eq!(ctx_day.delivery_style, DeliveryStyle::Normal);
        assert_eq!(ctx_day.volume_scale, 1.0);
    }

    #[test]
    fn test_zero_silence_fillers_multilingual() {
        let engine = ReflexEngine::new();

        // Italian
        let out_it = engine.evaluate("spiegami la relatività generale", 0.15, 140.0, 12);
        assert_eq!(out_it.language, "it");
        assert!(!out_it.immediate_utterance.text.is_empty());

        // English whisper at night
        let out_en_whisper = engine.evaluate("turn on the living room light please", 0.02, 140.0, 23);
        assert_eq!(out_en_whisper.acoustic.delivery_style, DeliveryStyle::Whisper);
        assert!(out_en_whisper.acoustic.volume_scale <= 0.4);
        assert!(!out_en_whisper.immediate_utterance.text.is_empty());
    }

    #[test]
    fn test_self_learning_plasticity() {
        let engine = ReflexEngine::new();

        let query = "attiva modalità relax in camera";
        // Initially unfamiliar
        let eval_before = engine.evaluate(query, 0.15, 140.0, 14);
        assert!(!eval_before.should_execute_fast);

        // System 2 resolves and reinforces the action
        let learned = engine.learn(query, "action_direct", "home_assistant.scene_relax");
        assert!(learned);

        // Now the engine knows it with high confidence!
        let eval_after = engine.evaluate(query, 0.15, 140.0, 14);
        let pred = eval_after.fast_prediction.expect("Must have prediction");
        assert_eq!(pred.intent, "action_direct");
        assert_eq!(pred.action, "home_assistant.scene_relax");
        assert!(pred.confidence >= 0.85);
    }
}
