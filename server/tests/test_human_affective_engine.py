import unittest
import numpy as np
import time
from server.features.human_affective_engine.interfaces import (
    MoodState,
    HeartRateMetrics,
    VoiceAcousticBiomarkers,
    OcularGazeBiomarkers,
    PhysiologicalMultimodalPayload,
)
from server.features.human_affective_engine.rppg_hemodynamic_extractor import hemodynamic_processor
from server.features.human_affective_engine.vocal_biomarker_extractor import vocal_biomarker_analyzer
from server.features.human_affective_engine.gaze_affect_profiler import gaze_affect_profiler
from server.features.human_affective_engine.affective_fusion_engine import affective_fusion_engine
from server.features.human_affective_engine.adaptive_response_orchestrator import adaptive_response_orchestrator

class HumanAffectiveEngineTest(unittest.TestCase):
    def test_rppg_hemodynamic_processor(self):
        t = np.linspace(0, 4.0, 120)
        optical_signal = 128.0 + (3.0 * np.sin(2 * np.pi * 1.2 * t))
        res = None
        for i, val in enumerate(optical_signal):
            res = hemodynamic_processor.push_optical_sample(float(val), time.time() + (i * 0.033))
        self.assertIsNotNone(res)
        self.assertGreaterEqual(res.bpm, 45.0)
        self.assertLessEqual(res.bpm, 185.0)

    def test_vocal_biomarker_extractor_depressive_monotone(self):
        flat_signal = np.ones(8000, dtype=np.float32) * 0.05
        bio = vocal_biomarker_analyzer.extract_biomarkers(flat_signal)
        self.assertGreater(bio.monotone_score, 0.5)

    def test_gaze_affect_profiler_downward_gaze(self):
        directions = ["down", "down", "down", "down", "center"]
        bio = gaze_affect_profiler.evaluate_gaze_sequence(directions, [1.0], [0.22, 0.23, 0.21])
        self.assertGreaterEqual(bio.downward_gaze_ratio, 0.6)
        self.assertGreater(bio.blunted_affect_indicator, 0.4)

    def test_affective_fusion_depressive_inference_and_warmth_strategy(self):
        payload = PhysiologicalMultimodalPayload(
            user_id="user_test_depressed",
            heart_metrics=HeartRateMetrics(
                bpm=62.0,
                hrv_rmssd_ms=18.0,
                signal_quality=0.9,
                pulse_confidence=0.88
            ),
            vocal_metrics=VoiceAcousticBiomarkers(
                pitch_f0_mean_hz=115.0,
                pitch_variability_st=8.0,
                jitter_percent=0.6,
                shimmer_percent=2.0,
                monotone_score=0.92,
                vocal_energy_rms=0.015,
                speech_pause_ratio=0.55,
                depressive_vocal_indicator=0.85
            ),
            ocular_metrics=OcularGazeBiomarkers(
                gaze_direction="down",
                downward_gaze_ratio=0.75,
                blink_rate_per_min=8.0,
                eye_aspect_ratio_mean=0.22,
                fixation_stagnation_score=0.7,
                blunted_affect_indicator=0.82
            )
        )
        result = affective_fusion_engine.infer_affective_state(payload)
        self.assertEqual(result.detected_mood, MoodState.DEPRESSED_DYSPHORIC)
        self.assertEqual(result.intervention_strategy_id, "INTERVENTION_EMPATHIC_WARMTH")
        self.assertIn("rassicurante", result.system_prompt_adaptation)
        self.assertEqual(result.voice_tone_guidance["warmth_level"], "maximum")

    def test_adaptive_response_orchestrator_prompt_modulation(self):
        payload = PhysiologicalMultimodalPayload(
            user_id="user_stress_01",
            heart_metrics=HeartRateMetrics(bpm=108.0, hrv_rmssd_ms=14.0, signal_quality=0.92, pulse_confidence=0.9),
            vocal_metrics=VoiceAcousticBiomarkers(
                pitch_f0_mean_hz=220.0, pitch_variability_st=32.0, jitter_percent=3.2,
                shimmer_percent=5.5, monotone_score=0.1, vocal_energy_rms=0.35,
                speech_pause_ratio=0.1, depressive_vocal_indicator=0.2
            ),
            ocular_metrics=OcularGazeBiomarkers(
                gaze_direction="center", downward_gaze_ratio=0.02, blink_rate_per_min=34.0,
                eye_aspect_ratio_mean=0.32, fixation_stagnation_score=0.3, blunted_affect_indicator=0.2
            )
        )
        inference = affective_fusion_engine.infer_affective_state(payload)
        adaptive_response_orchestrator.register_inference(inference)

        base_prompt = "Sei Nuxiva, un copilota operativo avanzato."
        modulated = adaptive_response_orchestrator.modulate_system_prompt("user_stress_01", base_prompt)
        self.assertIn("DIRETTIVA ADATTIVA STATO EMOTIVO", modulated)
        self.assertIn("ANXIOUS_STRESSED", modulated)

if __name__ == "__main__":
    unittest.main()
