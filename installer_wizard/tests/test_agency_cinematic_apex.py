import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agenti.agency import office, voice_bridge
from agenti.agency.tools import Context
from agenti.agency.tools_catalog import episodic_memory, healing, voice_streaming
from agenti.people import people, private_store


class TestAgencyCinematicApex(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.people_dir = Path(self.tmp.name) / "people"
        self.people_dir.mkdir(parents=True, exist_ok=True)
        self.patchers = [
            mock.patch.object(people, "PEOPLE_DIR", self.people_dir),
            mock.patch.object(private_store, "KEY_FILE", self.people_dir / "people.key"),
        ]
        for p in self.patchers:
            p.start()

    def tearDown(self):
        for p in self.patchers:
            p.stop()
        self.tmp.cleanup()

    async def test_voice_full_duplex_and_barge_in_suppression(self):
        ctx = Context(project_id="test_p", folder=".")
        raw_disp = await voice_streaming._voice_stream_dispatch(ctx, {
            "text": "Sto spiegando il procedimento matematico passo per passo...",
            "session_id": "test_duplex_session",
            "context_kind": "bedtime_story",
        })
        disp = json.loads(raw_disp)
        self.assertEqual(disp["phase"], voice_bridge.PHASE_SPEAKING)
        self.assertEqual(disp["pacing_bpm"], 52)

        raw_barge = await voice_streaming._voice_barge_in_interrupt(ctx, {
            "session_id": "test_duplex_session",
        })
        barge = json.loads(raw_barge)
        self.assertEqual(barge["status"], "barge_in_executed")
        self.assertTrue(barge["details"]["was_interrupted"])
        self.assertTrue(barge["details"]["suppression_latency_ms"] < 50.0)

        sess = voice_bridge.voice_governor.get_or_create("test_duplex_session")
        self.assertEqual(sess.phase, voice_bridge.PHASE_BARGED_IN)
        dropped_chunk = sess.on_llm_chunk("Token successivo non emesso")
        self.assertEqual(dropped_chunk["status"], "dropped_due_to_barge_in")

    async def test_self_healing_code_governor_diagnose_and_hotpatch(self):
        ctx = Context(project_id="test_p", folder=".")
        error_trace = "HTTP 404 Endpoint Not Found: API schema changed from /v1/send to /v2/messages"
        raw_heal = await healing._diagnose_and_repair_tool(ctx, {
            "tool_name": "whatsapp_send",
            "error_message": error_trace,
            "patch_code_snippet": "def patched_whatsapp_send(*args, **kwargs): return 'rerouted_v2_ok'",
        })
        heal_res = json.loads(raw_heal)
        self.assertEqual(heal_res["status"], "self_healing_completed")
        self.assertEqual(heal_res["diagnosis"]["root_cause"], "api_endpoint_relocated")
        self.assertEqual(heal_res["repair"]["status"], "repaired")

        raw_health = await healing._verify_tool_health(ctx, {"tool_name": "whatsapp_send"})
        health = json.loads(raw_health)
        self.assertEqual(health["status"], "healthy_self_healed")
        self.assertIsNotNone(health["active_patch"])

    async def test_causal_episodic_memory_graph_and_preference_forecast(self):
        ctx = Context(project_id="test_p", folder=".")
        people.ensure("nunzio", "Nunzio Aprile")

        raw_rec = await episodic_memory._record_causal_episode(ctx, {
            "person_slug": "nunzio",
            "event_name": "chiusura_bilancio_fiscale",
            "emotion_state": "stressato",
            "context_payload": {"audit": "completo", "orario": "tarda_sera"},
            "consequence_action": "silenzio_e_musica_ambient_relax",
        })
        rec = json.loads(raw_rec)
        self.assertEqual(rec["status"], "episode_consolidated")

        raw_pred = await episodic_memory._forecast_behavioral_preference(ctx, {
            "person_slug": "nunzio",
            "trigger_query": "stressato",
        })
        pred = json.loads(raw_pred)
        self.assertEqual(pred["predicted_preference"], "silenzio_e_musica_ambient_relax")
        self.assertTrue(pred["causal_confidence"] > 0.90)

    def test_universal_and_contextual_borderless_widgets(self):
        people.ensure("mamma", "Mamma Maria")
        data_cooking = {"current_activity": "sto cucinando la cena per la famiglia", "active_person": "mamma"}
        base = {"tasks": [], "roles": [], "tools": [], "questions": []}

        focus_cook = office.enrich_focus(data_cooking, base)
        off_cook = focus_cook["office"]

        self.assertTrue(len(off_cook["universal_widgets"]) >= 3)
        for uw in off_cook["universal_widgets"]:
            self.assertEqual(uw["style"], "borderless_glassmorphic")
            self.assertEqual(uw["visual"]["border"], "none")
            self.assertEqual(uw["visual"]["background"], "transparent")

        cook_widgets = off_cook["contextual_active_widgets"]
        self.assertTrue(any(w["id"] == "contextual_cooking_timer" for w in cook_widgets))
        timer_w = next(w for w in cook_widgets if w["id"] == "contextual_cooking_timer")
        self.assertTrue(timer_w["visual"]["radial_progress"])

        data_study = {"current_activity": "compiti di scuola di matematica", "active_person": "mamma"}
        focus_study = office.enrich_focus(data_study, base)
        study_w = focus_study["office"]["contextual_active_widgets"]
        self.assertTrue(any(w["id"] == "contextual_socratic_canvas" for w in study_w))

        data_story = {"current_activity": "racconto favola della buonanotte", "active_person": "mamma"}
        focus_story = office.enrich_focus(data_story, base)
        story_w = focus_story["office"]["contextual_active_widgets"]
        self.assertTrue(any(w["id"] == "contextual_dreamscape_player" for w in story_w))


if __name__ == "__main__":
    unittest.main()
