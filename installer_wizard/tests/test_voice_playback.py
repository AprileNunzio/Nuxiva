import unittest
from unittest.mock import AsyncMock, patch

from features.voices.playback import get_playback_commands, play_host_audio


class VoicePlaybackTest(unittest.IsolatedAsyncioTestCase):
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
        with patch("features.voices.playback.get_playback_commands", return_value=[["paplay", "-"], ["aplay", "-q", "-"]]):
            failing_proc = AsyncMock()
            failing_proc.communicate.return_value = (b"", b"connection refused")
            failing_proc.returncode = 1

            success_proc = AsyncMock()
            success_proc.communicate.return_value = (b"", b"")
            success_proc.returncode = 0

            with patch("asyncio.create_subprocess_exec", side_effect=[failing_proc, success_proc]):
                res = await play_host_audio(b"RIFFmockwavdata")
                self.assertTrue(res)
