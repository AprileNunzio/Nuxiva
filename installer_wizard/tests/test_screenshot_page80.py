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

from agenti.nodes import commands, screenshot_bridge, screenshot_intent, screenshot_local, screenshot_service

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
                mock.patch.object(screenshot_service, "STEP", 0), \
                mock.patch.object(screenshot_local, "capture") as local, \
                mock.patch.object(commands, "read_env", return_value={"NUXIVA_UI_LANG": "it"}):
            speech, ui = asyncio.run(commands.answer("fai uno screenshot"))
        request.assert_called_once_with()
        local.assert_not_called()
        self.assertIn("/srv/condivisa/05 Scambio/Screenshot", speech)
        self.assertEqual(ui, {"mode": "face"})

    def test_remote_browser_is_explained(self):
        from agenti.chat import context
        with mock.patch.object(commands, "read_env", return_value={"NUXIVA_UI_LANG": "en"}):
            token = context.device.set("remote")
            try:
                speech, _ = asyncio.run(commands.answer("take a screenshot"))
            finally:
                context.device.reset(token)
        self.assertEqual(speech, commands.phrase("remote", "en"))


class FallbackTests(unittest.TestCase):
    def setUp(self):
        screenshot_bridge._memory["value"] = None

    def test_missing_native_service_falls_back_to_a_direct_capture(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root = Path(tmp)
            env = {"NUXIVA_SCREENSHOT_TARGET": str(root)}
            with mock.patch.object(screenshot_local, "ALLOWED_ROOTS", (str(root),)), \
                    mock.patch.object(screenshot_local, "read_env", return_value=env), \
                    mock.patch.object(screenshot_local, "grab", return_value=screenshot_local.PNG + b"data"), \
                    mock.patch.object(screenshot_local, "GUEST_FLAG", root / "none"), \
                    mock.patch.object(screenshot_bridge, "RUNTIME", root / "missing"):
                report = asyncio.run(screenshot_service.take())
            self.assertEqual(report["status"], "saved", report)
            stored = list((root / "05 Scambio" / "Screenshot").iterdir())
            self.assertEqual([p.name for p in stored], [report["name"]])
            self.assertEqual(stored[0].read_bytes(), screenshot_local.PNG + b"data")
            self.assertEqual(screenshot_bridge.latest()["id"], report["id"])

    def test_fallback_respects_settings_and_privacy(self):
        with self.assertRaises(screenshot_local.LocalError) as off:
            screenshot_local.settings({"NUXIVA_SCREENSHOT": "0"})
        self.assertEqual(off.exception.status, "disabled")
        with self.assertRaises(screenshot_local.LocalError) as masked:
            screenshot_local.settings({"NUXIVA_SCREENSHOT_MASK": "0,0,10,10"})
        self.assertEqual(masked.exception.status, "blocked")
        for bad in ({"NUXIVA_SCREENSHOT_TARGET": "/etc"}, {"NUXIVA_SCREENSHOT_SUBDIR": "../x"}):
            with self.assertRaises(screenshot_local.LocalError):
                screenshot_local.settings(bad)
        self.assertEqual(screenshot_local.settings({})[1], "05 Scambio/Screenshot")
        self.assertTrue(screenshot_bridge.NAME.match(screenshot_local.file_name(3, 0)))

    def test_symlinked_subfolder_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            os.symlink(outside, Path(tmp) / "05 Scambio")
            with self.assertRaises(screenshot_local.LocalError):
                screenshot_local.directory(Path(tmp), "05 Scambio/Screenshot")


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
