import json
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
for p in (str(_ROOT), str(_ROOT / "installer_wizard"), str(_ROOT / "installer_wizard" / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from agenti.nodes import screenshot

NODES = _ROOT / "installer_wizard" / "agenti" / "infrastruttura" / "nodes"
SHOT_KEYS = {
    "NUXIVA_SCREENSHOT", "NUXIVA_SCREENSHOT_TARGET", "NUXIVA_SCREENSHOT_SUBDIR", "NUXIVA_SCREENSHOT_MASK",
    "NUXIVA_SCREENSHOT_RETENTION_DAYS", "NUXIVA_SCREENSHOT_BLOCK_LOCKED", "NUXIVA_SCREENSHOT_BLOCK_GUESTS",
    "NUXIVA_SCREENSHOT_NOTICE",
}


class ScreenshotSettingsTests(unittest.TestCase):
    def test_default_target_uses_the_server_host(self):
        on = {"NUXIVA_SCREENSHOT": "1", "NUXIVA_SCREENSHOT_TARGET": ""}
        self.assertEqual(screenshot.with_default_target(on, "192.168.1.5")["NUXIVA_SCREENSHOT_TARGET"], "smb://192.168.1.5/condivisa")
        self.assertEqual(screenshot.with_default_target(on, "nas.local")["NUXIVA_SCREENSHOT_TARGET"], "smb://nas.local/condivisa")

    def test_default_target_is_not_applied_when_off_or_set_or_hostile(self):
        off = {"NUXIVA_SCREENSHOT": "0"}
        self.assertIs(screenshot.with_default_target(off, "nas"), off)
        custom = {"NUXIVA_SCREENSHOT": "1", "NUXIVA_SCREENSHOT_TARGET": "/mnt/x"}
        self.assertIs(screenshot.with_default_target(custom, "nas"), custom)
        on = {"NUXIVA_SCREENSHOT": "1"}
        for host in ("", "-oProxy", "a b", "a;b", "a/b", "x" * 300):
            self.assertIs(screenshot.with_default_target(on, host), on)

    def test_every_language_labels_every_key(self):
        feature = json.loads((NODES / "feature.json").read_text(encoding="utf-8"))
        self.assertEqual({s["key"] for s in feature["settings"]}, SHOT_KEYS)
        for lang in ("it", "en", "fr", "es"):
            labels = json.loads((NODES / "language" / f"{lang}.json").read_text(encoding="utf-8"))["settings"]
            self.assertTrue(SHOT_KEYS <= set(labels), lang)
            self.assertTrue(all(labels[k].strip() for k in SHOT_KEYS), lang)

    def test_keys_are_editable_per_node(self):
        config_text = (_ROOT / "installer_wizard" / "backend" / "config.py").read_text(encoding="utf-8")
        for key in SHOT_KEYS:
            self.assertIn(f'"{key}"', config_text)


if __name__ == "__main__":
    unittest.main()
