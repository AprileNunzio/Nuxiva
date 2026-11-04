import unittest
from unittest.mock import AsyncMock, patch

from features.voices.playback import get_playback_commands, play_host_audio


class VoicePlaybackTest(unittest.IsolatedAsyncioTestCase):
    def test_paplay_uses_implicit_stdin_for_direct_and_kiosk_commands(self):
        with patch.dict("os.environ", {"NUXIVA_PLAY_CMD": ""}), \
             patch("features.voices.playback.shutil.which", side_effect=lambda name: name), \
             patch("features.voices.playback._get_kiosk_uid", return_value=1000), \
             patch("features.voices.playback.os.name", "posix"), \
             patch("features.voices.playback.os.getuid", return_value=0, create=True):
            commands = get_playback_commands()
        self.assertIn(["paplay"], commands)
        kiosk = next(cmd for cmd in commands if cmd[0] == "runuser")
        self.assertEqual(kiosk[-1], "paplay")
        self.assertIn("XDG_RUNTIME_DIR=/run/user/1000", kiosk)
        self.assertIn(["pw-play", "-"], commands)
        self.assertIn(["aplay", "-q", "-"], commands)

    def test_wake_wav_is_valid_non_silent_pcm(self):
        import io
        import struct
        import wave
        from features.voices.feedback import wake_wav
        with wave.open(io.BytesIO(wake_wav()), "rb") as wav:
            self.assertEqual((wav.getnchannels(), wav.getsampwidth(), wav.getframerate()), (1, 2, 16000))
            self.assertAlmostEqual(wav.getnframes() / wav.getframerate(), 0.58, places=3)
            pcm = wav.readframes(wav.getnframes())
        peak = max(abs(s[0]) for s in struct.iter_unpack("<h", pcm))
        self.assertGreater(peak, 100)
        self.assertLess(peak, 10000)

    def test_get_playback_commands_custom(self):
        with patch.dict("os.environ", {"NUXIVA_PLAY_CMD": "custom-play -v"}):
            cmds = get_playback_commands()
            self.assertEqual(cmds[0], ["custom-play", "-v"])

    async def test_play_host_audio_empty(self):
        res = await play_host_audio(b"")
        self.assertFalse(res)

    async def test_play_host_audio_success(self):
        with patch("features.voices.playback.get_playback_commands", return_value=[["aplay", "-q", "-"]]):
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (b"", b"")
            mock_proc.returncode = 0
            with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                res = await play_host_audio(b"RIFFmockwavdata")
                self.assertTrue(res)

    async def test_play_host_audio_fallback(self):
        with patch("features.voices.playback.get_playback_commands", return_value=[["paplay"], ["aplay", "-q", "-"]]):
            failing_proc = AsyncMock()
            failing_proc.communicate.return_value = (b"", b"connection refused")
            failing_proc.returncode = 1

            success_proc = AsyncMock()
            success_proc.communicate.return_value = (b"", b"")
            success_proc.returncode = 0

            with patch("asyncio.create_subprocess_exec", side_effect=[failing_proc, success_proc]):
                with self.assertLogs("nuxiva.voice.playback", level="WARNING"):
                    res = await play_host_audio(b"RIFFmockwavdata")
                self.assertTrue(res)
