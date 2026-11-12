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
    async def test_capture_cancellation_reaps_process_and_unregisters_session(self):
        from types import SimpleNamespace
        started = asyncio.Event()

        async def read(_):
            started.set()
            await asyncio.Event().wait()

        process = SimpleNamespace(stdout=SimpleNamespace(read=read), stderr=None,
                                  terminate=MagicMock(), kill=MagicMock(), wait=AsyncMock(return_value=0))
        class CaptureSession:
            def __init__(self, socket):
                self.ws = socket

        capture = HostMicCapture(CaptureSession)
        with patch("features.ear.host_mic.get_capture_candidates", return_value=[["capture"]]), \
             patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=process)):
            task = asyncio.create_task(capture.run())
            await asyncio.wait_for(started.wait(), 1)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await asyncio.wait_for(task, 1)
        self.assertIsNone(capture.process)
        self.assertIsNone(capture.session)
        process.wait.assert_awaited()
        self.assertEqual(len(_get_sessions()), 0)

    async def test_capture_diagnostics_are_drained_with_bounded_memory(self):
        capture = HostMicCapture(lambda socket: socket)
        stream = MagicMock()
        stream.read = AsyncMock(side_effect=[b"x" * 4096, b"y" * 4096, b""])
        await capture._drain_stderr(stream)
        self.assertEqual(capture._stderr_tail, b"y" * 2048)

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

    def test_native_capture_requests_low_latency(self):
        from features.ear import host_mic
        with patch.dict("os.environ", {}, clear=True), \
             patch("features.ear.host_mic.shutil.which", return_value="/usr/bin/tool"), \
             patch("features.ear.host_mic._get_kiosk_uid", return_value=None):
            commands = host_mic.get_capture_candidates()
        parec = [c for c in commands if c[0] == "parec"]
        self.assertEqual(len(parec), 1)
        self.assertIn("--latency-msec=30", parec[0])
        self.assertIn("--latency=30ms", next(c for c in commands if c[0] == "pw-record"))
        arecord = next(c for c in commands if c[0] == "arecord")
        self.assertIn("--period-time=30000", arecord)
        self.assertIn("--buffer-time=240000", arecord)
        with patch.dict("os.environ", {"NUXIVA_MIC_LATENCY_MS": "5000"}):
            self.assertEqual(host_mic.capture_latency_ms(), 200)
        with patch.dict("os.environ", {"NUXIVA_MIC_LATENCY_MS": "abc"}):
            self.assertEqual(host_mic.capture_latency_ms(), 30)

    def test_kiosk_capture_keeps_latency_hint(self):
        from features.ear import host_mic
        with patch.dict("os.environ", {}, clear=True), \
             patch("features.ear.host_mic.shutil.which", side_effect=lambda name: name in ("parec", "runuser") and name), \
             patch("features.ear.host_mic._get_kiosk_uid", return_value=1001), \
             patch("features.ear.host_mic.os.getuid", return_value=0, create=True), \
             patch("features.ear.host_mic.os.name", "posix"):
            commands = host_mic.get_capture_candidates()
        self.assertEqual(commands[0][:3], ["runuser", "-u", host_mic.KIOSK_USER])
        self.assertIn("--latency-msec=30", commands[0])

    async def test_wake_feedback_loads_voice_modules_without_features_package(self):
        import importlib
        from features.ear import host_mic
        real_import = importlib.import_module

        def isolated(name, *args, **kwargs):
            if name.startswith(("features.voices", "installer_wizard.features.voices")):
                raise ModuleNotFoundError(name)
            return real_import(name, *args, **kwargs)

        for name in ("feedback", "playback"):
            sys.modules.pop(f"_nuxiva_host_voices_{name}", None)
        try:
            with patch("features.ear.host_mic.importlib.import_module", side_effect=isolated):
                feedback = host_mic._voice_module("feedback")
                playback = host_mic._voice_module("playback")
                self.assertTrue(feedback.wake_wav().startswith(b"RIFF"))
                self.assertTrue(callable(playback.play_host_audio))
                self.assertIs(host_mic._voice_module("feedback"), feedback)
                with patch.object(playback, "play_host_audio", new_callable=AsyncMock) as play, \
                     patch.dict("os.environ", {"NUXIVA_EAR_HOST_WAKE_SOUND": "1"}):
                    await host_mic.play_wake_feedback()
                play.assert_awaited_once_with(feedback.wake_wav())
        finally:
            for name in ("feedback", "playback"):
                sys.modules.pop(f"_nuxiva_host_voices_{name}", None)

    def test_voice_module_loader_rejects_unknown_names(self):
        from features.ear import host_mic
        for name in ("../ear/service", "os", "synthesis"):
            with self.assertRaises(ValueError):
                host_mic._voice_module(name)

    async def test_native_pcm_is_conditioned_before_session_feed(self):
        fed = []

        class MockSession:
            def __init__(self, ws):
                self.ws = ws
                self.page = {}
                self.last_pcm_time = 0.0

            async def feed(self, pcm):
                fed.append(pcm)

        capture = HostMicCapture(MockSession)
        capture.conditioner = MagicMock()
        capture.conditioner.process.side_effect = [b"", b"\x02\x00\x03\x00"]
        mock_proc = MagicMock()
        mock_proc.stderr = None
        mock_proc.stdout.read = AsyncMock(side_effect=[b"\x01\x00" * 4, b"\x01\x00" * 4, b""])
        mock_proc.terminate = MagicMock()
        mock_proc.wait = AsyncMock(return_value=0)
        with patch("features.ear.host_mic.get_capture_candidates", return_value=[["fake-rec"]]), \
             patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            run_task = asyncio.create_task(capture.run())
            await asyncio.sleep(0.05)
            capture.stop()
            run_task.cancel()
            try:
                await run_task
            except asyncio.CancelledError:
                pass
        capture.conditioner.restart.assert_called()
        self.assertEqual(fed, [b"\x02\x00\x03\x00"])

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
        mock_proc.stderr = None
        mock_proc.stdout.read = AsyncMock(side_effect=[b"pcmchunk", b""])
        mock_proc.terminate = MagicMock()
        mock_proc.wait = AsyncMock(return_value=0)

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
