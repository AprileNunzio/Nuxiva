import asyncio
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_ROOT = Path(__file__).resolve().parents[2]
for p in (str(_ROOT), str(_ROOT / "installer_wizard"), str(_ROOT / "installer_wizard" / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from agenti.nodes import commands, screenshot_bridge, screenshot_intent

NODES = _ROOT / "installer_wizard" / "agenti" / "infrastruttura" / "nodes"
DISPLAY = _ROOT / "installer_wizard" / "web" / "display"
STATUSES = ("saved", "queued", "blocked", "failed", "disabled", "no_target", "delivered_later")


class BridgeTests(unittest.TestCase):
    def test_request_creates_the_flag_only_in_a_real_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            screenshot_bridge.request(root)
            self.assertTrue((root / "request").is_file())
            with self.assertRaises(screenshot_bridge.BridgeUnavailable):
                screenshot_bridge.request(root / "missing")
            os.symlink(tmp, root / "link")
            with self.assertRaises(screenshot_bridge.BridgeUnavailable):
                screenshot_bridge.request(root / "link")

    def test_status_is_validated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsNone(screenshot_bridge.latest(root))
            good = {"id": 5, "status": "saved", "name": "server_20261124-110000_000.png", "folder": "/srv/x\x07", "count": 0}
            (root / "status.json").write_text(json.dumps(good))
            self.assertEqual(screenshot_bridge.latest(root),
                             {"id": 5, "status": "saved", "name": "server_20261124-110000_000.png", "folder": "/srv/x", "count": 0})
            (root / "status.json").write_text(json.dumps({**good, "name": "../x.png", "status": "saved"}))
            self.assertEqual(screenshot_bridge.latest(root)["name"], "")
            for bad in ({**good, "status": "rm"}, {**good, "id": "x"}, [], "{"):
                (root / "status.json").write_text(bad if isinstance(bad, str) else json.dumps(bad))
                self.assertIsNone(screenshot_bridge.latest(root))
            (root / "status.json").write_text("x" * 5000)
            self.assertIsNone(screenshot_bridge.latest(root))


class VoiceTests(unittest.TestCase):
    def test_intent_matches_requests_only(self):
        self.assertTrue(screenshot_intent.asks("fai uno screenshot di quello che vedi"))
        self.assertFalse(screenshot_intent.asks("come si fa uno screenshot?"))

    def test_other_sentences_are_left_to_other_connectors(self):
        with self.assertRaises(LookupError):
            asyncio.run(commands.answer("che tempo fa domani"))

    def test_kiosk_request_waits_for_the_real_outcome(self):
        reports = iter([{"id": 1, "status": "saved", "name": "", "folder": "/a", "count": 0},
                        {"id": 2, "status": "saved", "name": "", "folder": "/srv/condivisa/05 Scambio/Screenshot", "count": 0}])
        with mock.patch.object(screenshot_bridge, "latest", side_effect=lambda: next(reports)), \
                mock.patch.object(screenshot_bridge, "request") as request, \
                mock.patch.object(commands, "STEP", 0), \
                mock.patch.object(commands, "read_env", return_value={"NUXIVA_UI_LANG": "it"}):
            speech, ui = asyncio.run(commands.answer("fai uno screenshot"))
        request.assert_called_once_with()
        self.assertIn("/srv/condivisa/05 Scambio/Screenshot", speech)
        self.assertEqual(ui, {"mode": "face"})

    def test_remote_browser_and_missing_service_are_explained(self):
        from agenti.chat import context
        with mock.patch.object(commands, "read_env", return_value={"NUXIVA_UI_LANG": "en"}):
            token = context.device.set("remote")
            try:
                speech, _ = asyncio.run(commands.answer("take a screenshot"))
            finally:
                context.device.reset(token)
            self.assertEqual(speech, commands.phrase("remote", "en"))
            with mock.patch.object(screenshot_bridge, "latest", return_value=None), \
                    mock.patch.object(screenshot_bridge, "request", side_effect=screenshot_bridge.BridgeUnavailable("x")):
                speech, _ = asyncio.run(commands.answer("take a screenshot"))
            self.assertEqual(speech, commands.phrase("service", "en"))


class TranslationTests(unittest.TestCase):
    def test_every_language_has_every_message(self):
        for lang in ("it", "en", "fr", "es"):
            voice = json.loads((NODES / "language" / f"{lang}.json").read_text(encoding="utf-8"))["screenshot_voice"]
            self.assertTrue(set(STATUSES) - {"delivered_later"} | {"remote", "service", "timeout"} <= set(voice), lang)
            page = json.loads((DISPLAY / "language" / f"{lang}.json").read_text(encoding="utf-8"))["dictionary"]
            for status in (*STATUSES, "service"):
                self.assertTrue(page.get(f"screenshot_{status}"), (lang, status))

    def test_nodes_feature_is_a_voice_connector(self):
        feature = json.loads((NODES / "feature.json").read_text(encoding="utf-8"))
        self.assertEqual((feature["connector"], feature["connector_risk"]), ("commands.py", "personal"))


if __name__ == "__main__":
    unittest.main()
