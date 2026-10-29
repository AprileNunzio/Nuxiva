import asyncio
import sys
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

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
    def test_public_port_default_and_explicit_url_overrides(self):
        import runpy
        from features.ear import host_mic
        with patch.dict("os.environ", {}, clear=True):
            defaults = runpy.run_path(host_mic.__file__)
        self.assertEqual(defaults["ASSISTANT_URL"], "http://127.0.0.1:80/api/assistant/chat")
        self.assertEqual(defaults["TTS_URL"], "http://127.0.0.1:80/api/voice/speak")
        with patch.dict("os.environ", {"NUXIVA_PUBLIC_PORT": "8888"}, clear=True):
            configured = runpy.run_path(host_mic.__file__)
        self.assertEqual(configured["TTS_URL"], "http://127.0.0.1:8888/api/voice/speak")
        with patch.dict("os.environ", {"NUXIVA_ASSISTANT_URL": "http://localhost:9000/chat",
                                       "NUXIVA_TTS_URL": "http://localhost:9000/speak"}):
            overrides = runpy.run_path(host_mic.__file__)
        self.assertEqual(overrides["ASSISTANT_URL"], "http://localhost:9000/chat")
        self.assertEqual(overrides["TTS_URL"], "http://localhost:9000/speak")

    async def test_wake_feedback_origin_deduplication_and_rearm(self):
        with patch("features.ear.host_mic.play_wake_feedback", new_callable=AsyncMock) as sound:
            sock = HeadlessSocket()
            await sock.send('{"type":"wake", "origin":false}')
            await asyncio.sleep(0)
            sound.assert_not_awaited()
            await sock.send('{"type":"wake"}')
            await sock.send('{"type":"wake_only"}')
            await sock.send('{"type":"state", "state":"listening", "conversation":true}')
            await asyncio.sleep(0)
            sound.assert_awaited_once()
            await sock.send('{"type":"state", "state":"idle"}')
            await sock.send('{"type":"wake_only"}')
            await asyncio.sleep(0)
            self.assertEqual(sound.await_count, 2)
            await sock.close()
            await sock.send('{"type":"wake"}')
            await asyncio.sleep(0)
            self.assertEqual(sound.await_count, 2)

    async def test_wake_playback_failure_and_opt_out(self):
        from features.ear.host_mic import play_wake_feedback
        with patch("features.voices.playback.play_host_audio", new_callable=AsyncMock) as play:
            with patch.dict("os.environ", {"NUXIVA_EAR_HOST_WAKE_SOUND": "0"}):
                await play_wake_feedback()
                play.assert_not_awaited()
            with patch.dict("os.environ", {"NUXIVA_EAR_HOST_WAKE_SOUND": "1"}):
                play.side_effect = OSError("no audio device")
                with self.assertLogs("nuxiva.ear.host_mic", level="WARNING"):
                    await play_wake_feedback()

    async def test_headless_requests_use_public_urls_and_preserve_payload(self):
        import json
        from features.ear.host_mic import dispatch_headless_command, PUBLIC_URL
        with patch("urllib.request.urlopen") as opened:
            response = MagicMock()
            response.__enter__.return_value = response
            response.read.side_effect = [b'{"reply":"Ciao"}', b'{"ok":true}']
            opened.return_value = response
            await dispatch_headless_command({"text": "saluta", "lang": "it", "speaker": "nunzio"})
            requests = [call.args[0] for call in opened.call_args_list]
            self.assertEqual([r.full_url for r in requests], [
                PUBLIC_URL + "/api/assistant/chat", PUBLIC_URL + "/api/voice/speak"])
            self.assertEqual(json.loads(requests[0].data)["speaker"], "nunzio")
            self.assertEqual(json.loads(requests[1].data), {"text": "Ciao", "lang": "it"})

    async def test_tts_negative_playback_result_is_logged_as_failure(self):
        with patch("urllib.request.urlopen") as opened:
            response = MagicMock()
            response.__enter__.return_value = response
            response.read.return_value = b'{"ok":false}'
            opened.return_value = response
            with self.assertLogs("nuxiva.ear.host_mic", level="WARNING"):
                await speak_reply("Ciao", "it")

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

    async def test_headless_socket_ignores_mirrored_transcripts(self):
        dispatched = []

        async def mock_dispatch(event):
            dispatched.append(event)

        with patch("features.ear.host_mic.dispatch_headless_command", mock_dispatch):
            sock = HeadlessSocket()
            # Un evento con origin=False rappresenta un broadcast mirror da un'altra sessione (es. display/kiosk)
            await sock.send('{"type": "transcript", "text": "ciao Nuxiva", "lang": "it", "origin": false}')
            await asyncio.sleep(0.05)

            self.assertEqual(len(dispatched), 0)

    async def test_host_mic_registers_and_unregisters_session_lifecycle(self):
        class MockSession:
            def __init__(self, ws):
                self.ws = ws
                self.page = {}
                self.last_pcm_time = 0.0

            async def feed(self, pcm):
                pass

        capture = HostMicCapture(MockSession)
        self.assertIsNone(capture.session)
        self.assertEqual(len(_get_sessions()), 0)

        mock_proc = MagicMock()
        mock_proc.stdout.read = MagicMock(side_effect=[b"pcmchunk", b""])
        mock_proc.terminate = MagicMock()
        mock_proc.wait = MagicMock(return_value=asyncio.sleep(0))

        with patch("features.ear.host_mic.get_capture_candidates", return_value=[["fake-rec"]]), \
             patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            run_task = asyncio.create_task(capture.run())
            await asyncio.sleep(0.05)

            # La sessione deve essere stata creata e registrata in SESSIONS
            self.assertIsNotNone(capture.session)
            self.assertIn(capture.session, _get_sessions())
            self.assertEqual(capture.session.page.get("id"), "host_mic")
            self.assertEqual(capture.session.page.get("page"), "host_mic")
            self.assertEqual(capture.session.page.get("visible"), "headless")

            # Quando si arresta la cattura, la sessione deve essere deregistrata
            capture.stop()
            await asyncio.sleep(0.05)
            run_task.cancel()
            try:
                await run_task
            except asyncio.CancelledError:
                pass

            self.assertIsNone(capture.session)
            self.assertEqual(len(_get_sessions()), 0)

    async def test_broadcast_event_delivers_transcript_to_registered_host_mic(self):
        from features.ear.broadcast import broadcast_event

        class MockSession:
            def __init__(self, ws):
                self.ws = ws
                self.page = {"id": "host_mic", "page": "host_mic", "visible": "headless"}

        sock = HeadlessSocket()
        session = MockSession(sock)
        _get_sessions().add(session)

        dispatched = []

        async def mock_dispatch(event):
            dispatched.append(event)

        with patch("features.ear.host_mic.dispatch_headless_command", mock_dispatch):
            # Simuliamo la chiamata broadcast da Session._deliver (origin=session)
            await broadcast_event(origin=session, type="transcript", text="accendi la luce", lang="it")
            await asyncio.sleep(0.05)

            self.assertEqual(len(dispatched), 1)
            self.assertEqual(dispatched[0]["text"], "accendi la luce")

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
