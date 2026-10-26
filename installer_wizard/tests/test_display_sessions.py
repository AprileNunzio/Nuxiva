import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from state import store
from features.desktop.desk import desk
from features.desktop.screens import screens
from system_api import DEFAULT_DISPLAY_SETTINGS, save_display_settings


class TestDisplaySessions(unittest.TestCase):
    def setUp(self):
        self.orig_display_settings = dict(store.display_settings) if isinstance(store.display_settings, dict) else {}
        self.orig_instances = dict(desk.instances)
        desk.instances.clear()

    def tearDown(self):
        store.display_settings = self.orig_display_settings
        desk.instances.clear()
        desk.instances.update(self.orig_instances)

    def test_default_display_settings_has_session_mode_shared(self):
        self.assertIn("session_mode", DEFAULT_DISPLAY_SETTINGS)
        self.assertEqual(DEFAULT_DISPLAY_SETTINGS["session_mode"], "shared")

    def test_save_display_settings_updates_session_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("system_api.NUXIVA_DIR", Path(tmpdir)):
                saved = save_display_settings({"session_mode": "isolated"})
                self.assertEqual(saved["session_mode"], "isolated")
                self.assertEqual(store.display_settings["session_mode"], "isolated")

                saved_invalid = save_display_settings({"session_mode": "unknown_value"})
                self.assertEqual(saved_invalid["session_mode"], "shared")

    def test_screens_assign_shared_mode_sets_screen_minus_one(self):
        items = [
            {"id": "meteo", "priority": 50, "size": "m"},
            {"id": "musica", "priority": 40, "size": "s"},
        ]
        assigned = screens.assign(items, wanted={}, session_mode="shared")
        for it in assigned:
            self.assertEqual(it["screen"], -1)

    def test_screens_assign_isolated_mode_assigns_physical_screens(self):
        items = [
            {"id": "meteo", "priority": 50, "size": "m"},
        ]
        assigned = screens.assign(items, wanted={}, session_mode="isolated")
        for it in assigned:
            self.assertEqual(it["screen"], 0)

    def test_desk_show_and_active_preserves_client_id(self):
        desk.widgets["test_wid"] = {
            "id": "test_wid", "name": "Test", "icon": "test", "rev": "1",
            "has_css": False, "size": "m", "replaces": [], "intents": ["test_intent"],
        }
        desk.show("test_wid", {"value": 123}, key="test_key", client_id="client_studio_99")
        self.assertIn("test_key", desk.instances)
        self.assertEqual(desk.instances["test_key"].get("client_id"), "client_studio_99")

        active_items = desk.active()
        matched = [i for i in active_items if i.get("key") == "test_key"]
        self.assertTrue(len(matched) > 0)
        self.assertEqual(matched[0].get("client_id"), "client_studio_99")

    def test_desk_on_intent_propagates_client_id(self):
        desk.widgets["test_intent_wid"] = {
            "id": "test_intent_wid", "name": "Intent Widget", "icon": "test", "rev": "1",
            "has_css": False, "size": "m", "replaces": [], "intents": ["weather_query"],
        }
        desk.on_intent("weather_query", {"title": "Meteo Roma"}, client_id="client_tablet_42")
        self.assertIn("test_intent_wid", desk.instances)
        self.assertEqual(desk.instances["test_intent_wid"].get("client_id"), "client_tablet_42")

    def test_state_snapshot_includes_live_dialogue(self):
        store.live_dialogue = {
            "id": "dlg_test_1",
            "user_text": "che tempo fa",
            "reply": "Oggi c'è il sole a Roma",
            "intent": "weather",
            "device": "remote",
            "client_id": "client_mac_studio",
            "ts": 123456789.0,
        }
        snap = store.snapshot()
        self.assertIn("live_dialogue", snap)
        self.assertEqual(snap["live_dialogue"]["client_id"], "client_mac_studio")
        self.assertEqual(snap["live_dialogue"]["user_text"], "che tempo fa")


if __name__ == "__main__":
    unittest.main()
