import asyncio
import json
import unittest
import unittest.mock
from pathlib import Path

FEATURES = Path(__file__).resolve().parents[1] / "features"
CONFIGURED = ("research", "fleet", "brain", "location", "study", "avatars", "models3d", "firewall", "vpn", "telegram", "experts")


class SettingsContractTest(unittest.TestCase):
    def test_configurable_features_declare_labelled_settings(self):
        for feature in CONFIGURED:
            manifest = json.loads((FEATURES / feature / "feature.json").read_text(encoding="utf-8"))
            keys = [item["key"] for item in manifest["settings"]]
            self.assertTrue(keys, feature)
            for lang in ("it", "en", "fr"):
                labels = json.loads((FEATURES / feature / "language" / f"{lang}.json").read_text(encoding="utf-8"))["settings"]
                self.assertEqual(sorted(labels), sorted(keys), f"{feature}/{lang}")

    def test_select_defaults_are_valid_options(self):
        for feature in CONFIGURED:
            manifest = json.loads((FEATURES / feature / "feature.json").read_text(encoding="utf-8"))
            for item in manifest["settings"]:
                if item["type"] == "select":
                    self.assertIn(item["default"], item["options"], item["key"])


class SurfaceTest(unittest.TestCase):
    def manifest(self, feature):
        return json.loads((FEATURES / feature / "feature.json").read_text(encoding="utf-8"))

    def test_system_options_leave_the_control_panel(self):
        self.assertEqual(self.manifest("agent")["surface"], "settings")
        self.assertEqual(self.manifest("redalert")["surface"], "settings")
        self.assertEqual(self.manifest("auto_update")["surface"], "hidden")
        self.assertEqual(self.manifest("skills")["surface"], "hidden")

    def test_redalert_languages_cover_every_setting(self):
        keys = sorted(item["key"] for item in self.manifest("redalert")["settings"])
        for lang in ("it", "en", "fr"):
            labels = json.loads((FEATURES / "redalert" / "language" / f"{lang}.json").read_text(encoding="utf-8"))["settings"]
            self.assertEqual(sorted(labels), keys, lang)

    def test_registry_rejects_an_unknown_surface(self):
        from feature_registry import Registry
        with self.assertRaises(ValueError):
            Registry._validate({"id": "prova", "name": "Prova", "surface": "elsewhere"}, "prova")
        self.assertEqual(Registry._validate({"id": "prova", "name": "Prova"}, "prova")["surface"], "hub")


class FleetAutoCreateTest(unittest.TestCase):
    def test_creation_can_be_switched_off(self):
        from features.fleet import tools
        with unittest.mock.patch.object(tools, "env_get", return_value="0"):
            reply = asyncio.run(tools.fleet_create("Zeta", "scopo qualsiasi"))
        self.assertIn("disattivata", reply)


if __name__ == "__main__":
    unittest.main()
