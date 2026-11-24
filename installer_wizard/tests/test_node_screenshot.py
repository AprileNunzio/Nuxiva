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
        no_shares = {"NUXIVA_SHARES": "0"}
        self.assertIs(screenshot.with_default_target(no_shares, "nas"), no_shares)
        custom = {"NUXIVA_SCREENSHOT": "1", "NUXIVA_SCREENSHOT_TARGET": "/mnt/x"}
        self.assertEqual(screenshot.with_default_target(custom, "nas"), custom)
        on = {"NUXIVA_SCREENSHOT": "1"}
        for host in ("", "-oProxy", "a b", "a;b", "a/b", "x" * 300):
            self.assertEqual(screenshot.with_default_target(on, host), on)

    def test_screenshots_are_on_by_default_when_the_share_exists(self):
        unset = screenshot.with_default_target({"NUXIVA_SCREENSHOT": ""}, "10.0.0.2")
        self.assertEqual(unset["NUXIVA_SCREENSHOT"], "1")
        self.assertEqual(unset["NUXIVA_SCREENSHOT_TARGET"], "smb://10.0.0.2/condivisa")

    def test_server_share_credentials_go_only_with_the_server_target(self):
        settings = screenshot.with_default_target({}, "nas")
        env = {"NUXIVA_SMB_PASSWORD": "Batteria-42"}
        self.assertEqual(screenshot.credentials(settings, "nas", env),
                         {"target": "smb://nas/condivisa", "user": "nuxiva-share", "password": "Batteria-42"})
        other = {**settings, "NUXIVA_SCREENSHOT_TARGET": "smb://altro/dati"}
        self.assertEqual(screenshot.credentials(other, "nas", env), {})
        custom = {**other, "NUXIVA_SCREENSHOT_SMB_USER": "mario"}
        self.assertEqual(screenshot.credentials(custom, "nas", {**env, "NUXIVA_SCREENSHOT_SMB_PASSWORD": "Altra-7"}),
                         {"target": "smb://altro/dati", "user": "mario", "password": "Altra-7"})
        self.assertEqual(screenshot.credentials({**settings, "NUXIVA_SCREENSHOT": "0"}, "nas", env), {})
        self.assertEqual(screenshot.credentials(settings, "nas", {"NUXIVA_SMB_PASSWORD": "a\nb"}), {})
        self.assertEqual(screenshot.credentials({**custom, "NUXIVA_SCREENSHOT_SMB_USER": "a b"}, "nas",
                                                {"NUXIVA_SCREENSHOT_SMB_PASSWORD": "x"}), {})

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
