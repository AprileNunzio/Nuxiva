import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from features.cameras.capture import CameraCapture


class PersistentCaptureTest(unittest.IsolatedAsyncioTestCase):
    async def test_stream_and_snapshot_share_capture_and_release_viewer_slot(self):
        from features.cameras import live
        source = {'id': 'bench', 'kind': 'local', 'main': False, 'device': '/dev/video4'}
        jpeg = b'\xff\xd8frame\xff\xd9'
        before = live._active['count']
        with patch.object(live, 'ffmpeg_command', return_value=['shared-camera']), \
             patch.object(live.capture, 'snapshot', new=AsyncMock(return_value=jpeg)) as read:
            response = await live.stream(source)
            part = await anext(response.body_iterator)
            self.assertIn(b'Content-Type: image/jpeg\r\n', part)
            self.assertIn(jpeg, part)
            await response.body_iterator.aclose()
            self.assertEqual(await live.snapshot_bytes(source), jpeg)
        self.assertEqual(live._active['count'], before)
        self.assertEqual(read.await_args_list[0], read.await_args_list[-1])

    async def test_concurrent_readers_share_one_camera_process(self):
        stream = asyncio.StreamReader()
        process = type('Process', (), {})()
        process.stdout = stream
        process.returncode = None
        process.wait = AsyncMock()
        def kill():
            process.returncode = 0
            stream.feed_eof()
        process.kill = kill
        capture = CameraCapture(['camera'])
        with patch('features.cameras.capture.asyncio.create_subprocess_exec', new=AsyncMock(return_value=process)) as start:
            first = asyncio.create_task(capture.read())
            second = asyncio.create_task(capture.read())
            await asyncio.sleep(0)
            stream.feed_data(b'header\xff\xd8image\xff\xd9')
            self.assertEqual(await first, b'\xff\xd8image\xff\xd9')
            self.assertEqual(await second, b'\xff\xd8image\xff\xd9')
            self.assertEqual(await capture.read(), b'\xff\xd8image\xff\xd9')
            start.assert_awaited_once()
            capture.task.cancel()
            try:
                await capture.task
            except asyncio.CancelledError:
                pass
        process.wait.assert_awaited_once()
