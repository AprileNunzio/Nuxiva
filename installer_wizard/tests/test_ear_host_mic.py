import asyncio
import sys
import unittest
from unittest.mock import patch

from features.ear.host_mic import HeadlessSocket, HostMicCapture, pick_capture_binary


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

    def test_host_mic_should_capture_toggle(self):
        capture = HostMicCapture(lambda ws: ws)
        with patch.dict("os.environ", {"NUXIVA_EAR_HOST_MIC": "0"}):
            self.assertFalse(capture.should_capture())

        with patch.dict("os.environ", {"NUXIVA_EAR_HOST_MIC": "1"}):
            self.assertTrue(capture.should_capture())

    def test_host_mic_yields_to_visible_session(self):
        with patch.dict("os.environ", {"NUXIVA_EAR_HOST_MIC": "1"}):
            capture = HostMicCapture(lambda ws: ws)

            class MockSession:
                def __init__(self, visible):
                    self.page = {"visible": visible}

            session = MockSession("visible")
            _get_sessions().add(session)
            self.assertFalse(capture.should_capture())

            session.page["visible"] = "hidden"
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
