import asyncio
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

from features.ear.host_mic import (HeadlessSocket, HostMicCapture,
                                   get_capture_candidates, pick_capture_binary,
                                   speak_reply)


def _get_sessions() -> set:
    for mod_name in ("features.ear.broadcast", "broadcast", "installer_wizard.features.ear.broadcast"):
        if mod_name in sys.modules:
            mod = sys.modules[mod_name]
            if hasattr(mod, "SESSIONS"):
                return mod.SESSIONS
    try:
        from features.ear.broadcast import SESSIONS
        return SESSIONS
    except ImportError:
        try:
            from broadcast import SESSIONS
            return SESSIONS
        except ImportError:
            from installer_wizard.features.ear.broadcast import SESSIONS
            return SESSIONS


class EarHostMicTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        _get_sessions().clear()

    def tearDown(self):
        _get_sessions().clear()

    def test_pick_capture_binary(self):
        with patch.dict("os.environ", {"NUXIVA_MIC_CMD": "test-rec -r 16000"}):
            self.assertEqual(pick_capture_binary(), ["test-rec", "-r", "16000"])
            self.assertEqual(get_capture_candidates(), [["test-rec", "-r", "16000"]])

    def test_host_mic_should_capture_toggle(self):
        capture = HostMicCapture(lambda ws: ws)
        with patch.dict("os.environ", {"NUXIVA_EAR_HOST_MIC": "0"}):
            self.assertFalse(capture.should_capture())

        with patch.dict("os.environ", {"NUXIVA_EAR_HOST_MIC": "1"}):
            self.assertTrue(capture.should_capture())

    def test_host_mic_does_not_yield_to_mere_visible_page(self):
        with patch.dict("os.environ", {"NUXIVA_EAR_HOST_MIC": "1"}):
            capture = HostMicCapture(lambda ws: ws)

            class MockSession:
                def __init__(self, visible):
                    self.page = {"visible": visible}
                    self.last_pcm_time = 0.0

            session = MockSession("visible")
            _get_sessions().add(session)
            self.assertTrue(capture.should_capture())

    def test_host_mic_yields_only_to_active_pcm_stream(self):
        with patch.dict("os.environ", {"NUXIVA_EAR_HOST_MIC": "1"}):
            capture = HostMicCapture(lambda ws: ws)

            class MockStreamingSession:
                def __init__(self):
                    self.page = {"visible": "visible"}
                    self.last_pcm_time = time.time()

            session = MockStreamingSession()
            _get_sessions().add(session)
            self.assertFalse(capture.should_capture())

            session.last_pcm_time = time.time() - 5.0
            self.assertTrue(capture.should_capture())

    async def test_headless_socket_dispatch(self):
        dispatched = []

        async def mock_dispatch(event):
            dispatched.append(event)

        with patch("features.ear.host_mic.dispatch_headless_command", mock_dispatch):
            sock = HeadlessSocket()
            await sock.send('{"type": "transcript", "text": "ciao Nuxiva", "lang": "it"}')
            await asyncio.sleep(0.05)

            self.assertEqual(len(dispatched), 1)
            self.assertEqual(dispatched[0]["text"], "ciao Nuxiva")

    async def test_speak_reply_success_and_failure_logging(self):
        with patch("urllib.request.urlopen") as mock_open:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b'{"ok": true}'
            mock_resp.__enter__.return_value = mock_resp
            mock_open.return_value = mock_resp

            with self.assertLogs("nuxiva.ear.host_mic", level="INFO") as cm:
                await speak_reply("Risposta di prova", "it")
                self.assertTrue(any("Sintesi vocale TTS riprodotta" in log for log in cm.output))

        with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
            with self.assertLogs("nuxiva.ear.host_mic", level="WARNING") as cm:
                await speak_reply("Altra prova", "it")
                self.assertTrue(any("non riuscito" in log for log in cm.output))
