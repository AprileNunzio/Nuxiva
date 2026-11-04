import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "client_web" / "src"
WIZARD = ROOT / "installer_wizard"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def feature_ids():
    found = set()
    for folder in ("features", "apps"):
        for path in (WIZARD / folder).glob("*/feature.json"):
            found.add(load(path)["id"])
    return found


def app_manifests():
    return [load(p) for folder in ("apps", "core_apps") for p in (SRC / folder).glob("*/manifest.json")]


class ControlPanelLayoutTest(unittest.TestCase):
    def test_every_folded_feature_exists(self):
        known = feature_ids()
        for manifest in app_manifests():
            for ident in manifest.get("featureIds", []):
                self.assertIn(ident, known, f"{manifest['id']}:{ident}")

    def test_a_feature_belongs_to_one_application(self):
        owners = {}
        for manifest in app_manifests():
            for ident in manifest.get("featureIds", []):
                owners.setdefault(ident, []).append(manifest["id"])
        for ident, apps in owners.items():
            self.assertEqual(len(apps), 1, f"{ident}:{apps}")

    def test_removed_integration_leaves_no_trace(self):
        self.assertFalse((WIZARD / "features" / "spotify").exists())
        self.assertFalse((WIZARD / "widgets" / "spotify").exists())
        self.assertNotIn("spotify", feature_ids())
