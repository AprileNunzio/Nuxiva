import json
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
for p in (str(_ROOT / "installer_wizard"), str(_ROOT / "installer_wizard" / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from feature_localization import link_related, localize_feature


def item(fid, name, settings):
    return {"id": fid, "name": name, "settings": settings}


class RelatedSettingsTests(unittest.TestCase):

    def test_known_target_gets_its_localized_name(self):
        items = link_related([item("desktop", "Desktop", [{"key": "A", "see": "vision"}]), item("vision", "Vision and faces", [])])
        self.assertEqual(items[0]["settings"][0], {"key": "A", "see": "vision", "see_name": "Vision and faces"})

    def test_unknown_self_or_forged_targets_are_dropped(self):
        items = link_related([item("desktop", "Desktop", [{"key": "A", "see": "ghost"}, {"key": "B", "see": "desktop"},
                                                          {"key": "C", "see": ["vision"], "see_name": "<b>x</b>"}]),
                              item("vision", "Vision", [])])
        for setting in items[0]["settings"]:
            self.assertNotIn("see", setting)
            self.assertNotIn("see_name", setting)

    def test_names_are_bounded(self):
        items = link_related([item("a", "A", [{"key": "K", "see": "b"}]), item("b", "x" * 500, [])])
        self.assertEqual(len(items[0]["settings"][0]["see_name"]), 80)

    def test_presence_gate_points_to_vision_with_help_in_every_language(self):
        features = _ROOT / "installer_wizard" / "features"
        manifest = json.loads((features / "desktop" / "feature.json").read_text(encoding="utf-8"))
        gate = next(s for s in manifest["settings"] if s["key"] == "NUXIVA_DISPLAY_PRESENCE_GATE")
        self.assertEqual(gate["see"], "vision")
        manifest["dir"] = str(features / "desktop")
        vision = json.loads((features / "vision" / "feature.json").read_text(encoding="utf-8")) | {"dir": str(features / "vision")}
        for lang in ("it", "en", "fr", "es"):
            desk = localize_feature(manifest, lang)
            seen = localize_feature(vision, lang)
            linked = link_related([desk, seen])[0]
            setting = next(s for s in linked["settings"] if s["key"] == "NUXIVA_DISPLAY_PRESENCE_GATE")
            self.assertEqual(setting["see_name"], seen["name"])
            self.assertTrue(setting.get("help"), lang)
            live = next(s for s in seen["settings"] if s["key"] == "NUXIVA_LIVENESS")
            self.assertTrue(live.get("help"), lang)


if __name__ == "__main__":
    unittest.main()
