import json
import unittest
from pathlib import Path
from unittest import mock

from agenti.people import focus

ROOT = Path(__file__).resolve().parents[1]
WIDGETS = ROOT / "agenti" / "salute" / "medico" / "widget"
DISPLAY = ROOT / "web" / "display"


class HealthCardTest(unittest.TestCase):
    def card(self, values):
        view = {"values": values, "pulse": [[1, 60]], "recovery": None, "goals": {}, "signals": [], "sources": [], "at": 1.0}
        with mock.patch.object(focus, "_focus", return_value="anna"), \
                mock.patch.object(focus, "_who", return_value={"slug": "anna", "name": "Anna Rossi", "initials": "AR"}), \
                mock.patch.object(focus, "_kick"), mock.patch.object(focus.service, "health_view", return_value=view):
            return focus.health_card()

    def test_only_live_heart_hides_health_card(self):
        self.assertIsNone(self.card({"heart_rate": {"value": 53, "unit": "bpm", "kind": "camera", "age": 1}}))

    def test_health_card_never_carries_live_heart(self):
        card = self.card({"heart_rate": {"value": 53, "unit": "bpm", "kind": "band", "age": 1},
                          "spo2": {"value": 97, "unit": "%", "kind": "band", "age": 1}})
        self.assertEqual(set(card["values"]), {"spo2"})
        self.assertNotIn("pulse", card)
        self.assertNotIn("at", card)

    def test_empty_view_hides_health_card(self):
        self.assertIsNone(self.card({}))


class HeartWidgetTest(unittest.TestCase):
    def test_single_heart_widget(self):
        hub = (WIDGETS / "health_hub" / "widget.js").read_text(encoding="utf-8")
        self.assertNotIn("heart_rate", hub)
        self.assertNotIn("hh-heart", hub)
        beat = (WIDGETS / "vital_check" / "widget.js").read_text(encoding="utf-8")
        self.assertIn("vc-heart", beat)
        self.assertIn("vc-ecg", beat)
        self.assertNotIn("not_medical\"))}</p>", beat)

    def test_no_refresh_bar_or_refresh_tooltip(self):
        desk = (DISPLAY / "desk.js").read_text(encoding="utf-8")
        hud = (DISPLAY / "widgets_hud.css").read_text(encoding="utf-8")
        self.assertNotIn("w-cycle", desk)
        self.assertNotIn("refresh_every", desk)
        self.assertNotIn("w-cycle", hud)
        for lang in ("it", "en", "fr", "es"):
            common = json.loads((ROOT / "widgets" / "common" / "language" / f"{lang}.json").read_text(encoding="utf-8"))
            self.assertNotIn("refresh_every", common["dictionary"])

    def test_heart_widget_texts_are_translated(self):
        keys = None
        for lang in ("it", "en", "fr", "es"):
            words = json.loads((WIDGETS / "vital_check" / "language" / f"{lang}.json").read_text(encoding="utf-8"))["dictionary"]
            self.assertTrue(all(isinstance(v, str) and v for v in words.values()))
            keys = keys or set(words)
            self.assertEqual(set(words), keys)
        script = (WIDGETS / "vital_check" / "widget.js").read_text(encoding="utf-8")
        for key in ("title", "unit", "m_breath", "per_min", "aria_row", "not_medical", "src_device", "src_camera"):
            self.assertIn(f'"{key}"', script)
            self.assertIn(key, keys)

    def test_frameless_health_widgets(self):
        for wid in ("vital_check", "health_hub"):
            meta = json.loads((WIDGETS / wid / "widget.json").read_text(encoding="utf-8"))
            self.assertIs(meta.get("chrome"), False)


if __name__ == "__main__":
    unittest.main()
