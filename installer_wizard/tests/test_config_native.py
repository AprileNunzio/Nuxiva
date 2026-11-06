import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

for p in (str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[1] / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi import HTTPException

import config
import native_core
import settings

NATIVE = native_core.load()
SYMBOLS = ("RustSecretPolicy", "config_valid_key", "config_parse_env", "config_rewrite_env", "config_ollama_url",
           "config_normalize_ollama", "config_ollama_remote", "config_apply_plan", "config_reload_units")
READY = NATIVE is not None and all(hasattr(NATIVE, name) for name in SYMBOLS)

ENV_TEXT = ("# Nuxiva\nNUXIVA_A=1\nNUXIVA_A=2\n  NUXIVA_B = \"x y\"  \nlower=1\n'NUXIVA_Q'='z'\nnoeq\n\n"
            "NUXIVA_C=\"a\\$b\"\nNUXIVA_D='\"nested\"'\nGEMINI_API_KEY=\"segreto\"\nNUXIVA_E=é😀\n#fine\n")
KEYS = ["NUXIVA_SECRET_KEY", "GEMINI_API_KEY", "MY_TOKEN_FILE", "CREDENTIALS", "CREDENTIAL_X", "MONKEY_X",
        "NUXIVA_KEYBOARD", "NUXIVA_UI_LANG", "PASSWORDS", "X_COOKIE", "NUXIVA_PASSPHRASE_OLD", "TOKENS"]
OLLAMA = ["", "   ", "192.168.1.50", "192.168.1.50/", "http://x:99", "https://x", "x:abc", "http://a b",
          "http://a//b", "localhost:11434", " host:1 ", "[::1]:11434", "http://host:"]


@unittest.skipUnless(READY, "modulo nativo config-core non installato")
class ConfigParityTest(unittest.TestCase):

    def test_secrets_match(self):
        for key in KEYS:
            with self.subTest(key=key):
                self.assertEqual(config.is_secret(key), key in config.SECRET_KEYS or bool(config.SECRET_RE.search(key)))

    def test_parse_matches(self):
        self.assertEqual(config.parse_env(ENV_TEXT), config._py_parse_env(ENV_TEXT))

    def test_render_matches(self):
        cases = [{}, {"NUXIVA_A": "9"}, {"NUXIVA_B": ""}, {"NUXIVA_NEW": "'q'"}, {"NUXIVA_C": "$HOME"},
                 {"NUXIVA_A": "", "NUXIVA_Z": "z", "NUXIVA_Q": "\"w\""}]
        for updates in cases:
            with self.subTest(updates=updates):
                self.assertEqual(config.render_env(ENV_TEXT, updates), config._py_render_env(ENV_TEXT, updates))
        for updates in ({"lower": "1"}, {"NUXIVA_X": "a\nb"}):
            with self.subTest(updates=updates):
                with self.assertRaises(ValueError):
                    config.render_env(ENV_TEXT, updates)
                with self.assertRaises(ValueError):
                    config._py_render_env(ENV_TEXT, updates)

    def test_ollama_matches(self):
        for raw in OLLAMA:
            with self.subTest(raw=raw):
                self.assertEqual(config._ollama_address(raw), config._py_ollama_address(raw))
                try:
                    expected = settings._py_normalize_ollama(raw)
                except HTTPException:
                    expected = None
                try:
                    actual = settings.normalize_ollama(raw)
                except HTTPException:
                    actual = None
                self.assertEqual(actual, expected)

    def test_plans_match_python_table(self):
        keys = sorted({k for trigger, _ in settings.STEP_TRIGGERS for k in trigger})
        for key in keys + ["NUXIVA_UNKNOWN"]:
            with self.subTest(key=key):
                self.assertEqual(settings.plan_steps([key], ["kiosk"]), settings._py_plan_steps([key], ["kiosk"]))
        self.assertEqual(settings.plan_steps(keys), settings._py_plan_steps(keys, None))
        for key in ("NUXIVA_WAKE_WORD", "NUXIVA_EAR_GAIN", "NUXIVA_X", "NUXIVA_ASSISTANT_NAME"):
            with self.subTest(reload=key):
                with mock.patch.object(native_core, "symbol", return_value=None):
                    expected = settings.services_to_reload([key])
                self.assertEqual(settings.services_to_reload([key]), expected)


class ConfigFileTest(unittest.TestCase):

    def test_write_env_is_private_and_atomic_in_both_engines(self):
        for engine in ("rust", "python"):
            with self.subTest(engine=engine), tempfile.TemporaryDirectory() as tmp, \
                    mock.patch.object(config, "ENV_FILE", Path(tmp) / "nuxiva.env"), \
                    mock.patch.dict(os.environ, {}, clear=False):
                patch = mock.patch.object(native_core, "symbol", return_value=None) if engine == "python" or not READY \
                    else mock.patch.object(native_core, "load", wraps=native_core.load)
                with patch:
                    config.write_env({"NUXIVA_TEST_ONE": "uno", "NUXIVA_TEST_TWO": "due"})
                    config.write_env({"NUXIVA_TEST_TWO": ""})
                    path = Path(tmp) / "nuxiva.env"
                    self.assertEqual(path.read_text(encoding="utf-8"), 'NUXIVA_TEST_ONE="uno"\n')
                    self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                    self.assertNotIn("NUXIVA_TEST_TWO", os.environ)
                    with self.assertRaises(ValueError):
                        config.write_env({"NUXIVA_TEST_ONE": "x", "bad key": "y"})
                    self.assertEqual(os.environ.get("NUXIVA_TEST_ONE"), "uno")


if __name__ == "__main__":
    unittest.main()
