import types
import unittest
from unittest import mock

from permissions import os_access


def fake_winreg(values: dict):
    module = types.SimpleNamespace(HKEY_LOCAL_MACHINE="HKLM", HKEY_CURRENT_USER="HKCU")

    class Key:
        def __init__(self, hive, path):
            self.entry = values.get((hive, path.rsplit("\\", 1)[-1]))
            if self.entry is None:
                raise FileNotFoundError

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    module.OpenKey = Key
    module.QueryValueEx = lambda key, name: (key.entry, 1)
    return module


class StateTest(unittest.TestCase):
    def state(self, values, kind="microphone"):
        with mock.patch.object(os_access, "winreg", fake_winreg(values)):
            return os_access.state(kind)

    def test_deny_in_either_hive_wins(self):
        self.assertEqual(self.state({("HKLM", "microphone"): "Allow", ("HKCU", "microphone"): "Deny"}), "deny")
        self.assertEqual(self.state({("HKLM", "microphone"): "Deny", ("HKCU", "microphone"): "Allow"}), "deny")

    def test_allow_and_unknown(self):
        self.assertEqual(self.state({("HKCU", "webcam"): "Allow"}, "webcam"), "allow")
        self.assertEqual(self.state({}, "location"), "unknown")

    def test_without_winreg_nothing_is_blocked(self):
        with mock.patch.object(os_access, "winreg", None):
            self.assertEqual(os_access.blocked(os_access.KINDS), [])

    def test_unknown_kind_is_rejected(self):
        with self.assertRaises(KeyError):
            os_access.state("keylogger")

    def test_settings_pages_are_fixed_system_uris(self):
        for kind in os_access.KINDS:
            self.assertTrue(os_access.settings_uri(kind).startswith("ms-settings:privacy-"))

    def test_every_kind_has_text_in_all_languages(self):
        import json
        from pathlib import Path
        root = Path(os_access.__file__).resolve().parent.parent / "i18n"
        for language in ("it", "en", "fr", "es"):
            table = json.loads((root / f"{language}.json").read_text(encoding="utf-8"))
            for kind in os_access.KINDS:
                for part in ("name", "title", "what", "why", "how"):
                    self.assertIn(f"access.{kind}.{part}", table, (language, kind, part))


if __name__ == "__main__":
    unittest.main()
