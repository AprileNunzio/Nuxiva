import unittest
from server.core.orchestrator.system1_router import system1_router, System1Intent
from server.core.orchestrator.reflex_bridge import reflex_bridge

class TestReflexEngineIntegration(unittest.TestCase):
    def test_multilingual_language_and_fillers(self):
        # Italian
        dec_it = system1_router.classify_sync("spiega la teoria quantistica dei campi")
        self.assertEqual(dec_it.language, "it")
        self.assertTrue(len(dec_it.immediate_filler) > 0)
        self.assertIn(dec_it.delivery_style, ["normal", "night_discreet", "whisper"])

        # English
        dec_en = system1_router.classify_sync("please analyze the global supply chain architecture")
        self.assertEqual(dec_en.language, "en")
        self.assertTrue(len(dec_en.immediate_filler) > 0)

        # Spanish
        dec_es = system1_router.classify_sync("por favor explica la fotosintesis")
        self.assertEqual(dec_es.language, "es")
        self.assertTrue(len(dec_es.immediate_filler) > 0)

    def test_whisper_and_night_adaptation(self):
        # Whisper: energy RMS very low (0.02)
        dec_whisper = system1_router.classify_sync(
            "spegni la luce",
            vocal_energy_rms=0.02,
            pitch_hz=130.0,
            hour_of_day=15,
        )
        self.assertTrue(dec_whisper.is_whisper)
        self.assertEqual(dec_whisper.delivery_style, "whisper")
        self.assertLess(dec_whisper.volume_scale, 0.5)

        # Night time: 23:00, normal speech
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
        
        # Inizialmente non registrata come fast action garantita
        dec_before = system1_router.classify_sync(query)
        self.assertFalse(dec_before.is_reflex_guaranteed)

        # L'assistente / System 2 impara il mapping
        success = system1_router.learn(query, "action_direct", "home_assistant.scene_cinema")
        self.assertTrue(success)

        # Ora il Sistema 1 riconosce la query come azione diretta garantita
        dec_after = system1_router.classify_sync(query)
        self.assertEqual(dec_after.intent, System1Intent.ACTION_DIRECT)
        self.assertTrue(dec_after.is_reflex_guaranteed)
        self.assertEqual(dec_after.target_agent, "home_assistant")
        self.assertEqual(dec_after.direct_action, "scene_cinema")

if __name__ == "__main__":
    unittest.main()
