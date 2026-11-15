import unittest
from server.core.orchestrator.system1_router import system1_router, System1Intent
from server.core.orchestrator.reflex_bridge import reflex_bridge

class TestReflexEngineIntegration(unittest.TestCase):
    def setUp(self):
        # Register pure dynamic templates at runtime (worldwide modular compatibility)
        reflex_bridge.register_lexicon_template("it", "thinking", "normal", "Sto elaborando l'analisi...")
        reflex_bridge.register_lexicon_template("en", "thinking", "normal", "Processing analysis...")
        reflex_bridge.register_lexicon_template("es", "thinking", "normal", "Procesando análisis...")
        reflex_bridge.register_lexicon_template("it", "thinking", "whisper", "Un attimo...")
        reflex_bridge.register_lexicon_template("it", "thinking", "night", "Controllo per te...")

    def test_multilingual_language_and_fillers(self):
        dec_it = system1_router.classify_sync("spiega la teoria quantistica dei campi")
        self.assertEqual(dec_it.language, "it")
        self.assertTrue(len(dec_it.immediate_filler) > 0)
        self.assertIn(dec_it.delivery_style, ["normal", "night_discreet", "whisper"])

        dec_en = system1_router.classify_sync("please analyze the global supply chain architecture")
        self.assertEqual(dec_en.language, "en")
        self.assertTrue(len(dec_en.immediate_filler) > 0)

        dec_es = system1_router.classify_sync("por favor explica la fotosintesis")
        self.assertEqual(dec_es.language, "es")
        self.assertTrue(len(dec_es.immediate_filler) > 0)

    def test_whisper_and_night_adaptation(self):
        dec_whisper = system1_router.classify_sync(
            "spegni la luce",
            vocal_energy_rms=0.02,
            pitch_hz=130.0,
            hour_of_day=15,
        )
        self.assertTrue(dec_whisper.is_whisper)
        self.assertEqual(dec_whisper.delivery_style, "whisper")
        self.assertLess(dec_whisper.volume_scale, 0.5)

        dec_night = system1_router.classify_sync(
            "chiudi la porta",
            vocal_energy_rms=0.15,
            pitch_hz=140.0,
            hour_of_day=23,
        )
        self.assertTrue(dec_night.is_night)
        self.assertEqual(dec_night.delivery_style, "night_discreet")
        self.assertLessEqual(dec_night.volume_scale, 0.6)

    def test_self_learning_plasticity(self):
        query = "imposta atmosfera cinematografica in salotto"
        dec_before = system1_router.classify_sync(query)
        self.assertFalse(dec_before.is_reflex_guaranteed)

        success = system1_router.learn(query, "action_direct", "home_assistant.scene_cinema")
        self.assertTrue(success)

        dec_after = system1_router.classify_sync(query)
        self.assertEqual(dec_after.intent, System1Intent.ACTION_DIRECT)
        self.assertTrue(dec_after.is_reflex_guaranteed)
        self.assertEqual(dec_after.target_agent, "home_assistant")
        self.assertEqual(dec_after.direct_action, "scene_cinema")

    def test_fase1_duplex_barge_in(self):
        reflex_bridge.start_speaking("Analizzo i parametri della flotta...")
        res_abort = reflex_bridge.barge_in("Stop")
        self.assertEqual(res_abort["action"], "abort")

        reflex_bridge.start_speaking("Verifico i sensori...")
        res_steer = reflex_bridge.barge_in("Anzi controlla la rete")
        self.assertEqual(res_steer["action"], "steer")
        self.assertEqual(res_steer["semantic_token"], "conversation.interruption_steer")

    def test_fase2_gaze_gate(self):
        gaze_direct = reflex_bridge.gaze_gate(gaze_score=0.85, distance_meters=1.2, voice_proximity=0.3)
        self.assertTrue(gaze_direct["is_activated"])
        self.assertFalse(gaze_direct["requires_wakeword"])

        gaze_away = reflex_bridge.gaze_gate(gaze_score=0.20, distance_meters=3.0, voice_proximity=0.1)
        self.assertFalse(gaze_away["is_activated"])
        self.assertTrue(gaze_away["requires_wakeword"])

    def test_fase3_formal_oracle_zero_hallucination(self):
        math_res = reflex_bridge.formal_resolve("calcola 42 * 128")
        self.assertIsNotNone(math_res)
        self.assertTrue(math_res["certified_zero_hallucination"])
        self.assertEqual(math_res["formatted_value"], "5376")
        self.assertEqual(math_res["numeric_value"], 5376.0)

        hw_res = reflex_bridge.formal_resolve("quanta ram abbiamo?")
        self.assertIsNotNone(hw_res)
        self.assertIn("11.4 GB", hw_res["formatted_value"])

    def test_fase4_proactive_sentinel(self):
        advice_hot = reflex_bridge.proactive_inspect(
            cpu_temp_celsius=89.0,
            ram_pressure_ratio=0.85,
            threats_blocked=0,
            session_hours=1.0,
            hour_of_day=14,
        )
        self.assertTrue(advice_hot["should_intervene"])
        self.assertEqual(advice_hot["urgency"], "critical")
        self.assertEqual(advice_hot["semantic_reason"], "thermal_alert_critical")

        advice_sec = reflex_bridge.proactive_inspect(
            cpu_temp_celsius=52.0,
            ram_pressure_ratio=0.30,
            threats_blocked=4,
            session_hours=1.0,
            hour_of_day=15,
        )
        self.assertTrue(advice_sec["should_intervene"])
        self.assertEqual(advice_sec["urgency"], "medium")
        self.assertEqual(advice_sec["semantic_reason"], "network_threats_mitigated")

if __name__ == "__main__":
    unittest.main()
