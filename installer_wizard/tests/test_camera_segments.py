import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agenti.cameras import recorder as recorder_mod
from agenti.cameras import segments
from agenti.cameras.segments import SegmentError, strip_audio, video_args

HAS_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def _make(path: Path, audio: bool) -> None:
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=64x64:rate=5"]
    if audio:
        cmd += ["-f", "lavfi", "-i", "sine=frequency=440", "-c:a", "aac", "-shortest"]
    cmd += ["-t", "1", "-c:v", "mpeg4", str(path)]
    subprocess.run(cmd, check=True)


@unittest.skipUnless(HAS_FFMPEG, "ffmpeg non installato")
class StripAudioRegressionTest(unittest.TestCase):
    def test_video_only_segment_is_left_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "seg_20261113_050000.mp4"
            _make(path, audio=False)
            before = path.read_bytes()
            self.assertFalse(strip_audio(path))
            self.assertEqual(path.read_bytes(), before)

    def test_audio_is_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "seg_20261113_050000.mp4"
            _make(path, audio=True)
            self.assertTrue(strip_audio(path))
            self.assertEqual(segments.streams(path), {"video"})
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), [path.name])

    def test_empty_segment_has_specific_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "seg_20261113_050000.mp4"
            path.write_bytes(b"")
            with self.assertRaises(SegmentError) as ctx:
                strip_audio(path)
            self.assertEqual(ctx.exception.code, "segment_empty")
            self.assertTrue(ctx.exception.discard)

    def test_truncated_segment_has_specific_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "seg_20261113_050000.mp4"
            _make(path, audio=True)
            path.write_bytes(path.read_bytes()[:2048])
            with self.assertRaises(SegmentError) as ctx:
                strip_audio(path)
            self.assertEqual(ctx.exception.code, "segment_unreadable")
            self.assertTrue(ctx.exception.detail)
            self.assertTrue(ctx.exception.discard)


class StripFailureDetailTest(unittest.TestCase):
    def test_failure_carries_ffmpeg_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "seg_20261113_050000.mp4"
            path.write_bytes(b"x")
            failed = subprocess.CompletedProcess([], 1, b"", b"noise\n[mp4 @ 0x1] Could not find tag for codec\x07 pcm\n")
            with mock.patch.object(segments, "streams", return_value={"video", "audio"}), \
                    mock.patch.object(segments, "_exe", return_value="ffmpeg"), \
                    mock.patch.object(segments.subprocess, "run", return_value=failed):
                with self.assertRaises(SegmentError) as ctx:
                    strip_audio(path)
            self.assertEqual(ctx.exception.code, "audio_strip_failed")
            self.assertEqual(ctx.exception.detail, "[mp4 @ 0x1] Could not find tag for codec  pcm")
            self.assertFalse(ctx.exception.discard)
            self.assertEqual(path.read_bytes(), b"x")


class WebcamCodecTest(unittest.TestCase):
    def test_webcam_never_copies_raw_frames_into_mp4(self):
        self.assertNotIn("copy", video_args({"kind": "webcam"}))

    def test_network_camera_keeps_stream_copy(self):
        self.assertEqual(video_args({"kind": "rtsp"}), ["-c:v", "copy"])


class _Proc:
    returncode = None


class EncryptPendingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cam = {"id": "cam1", "name": "Ingresso"}
        self.incoming = self.root / "cam1" / "incoming"
        self.incoming.mkdir(parents=True)
        self.events = []
        self.rec = recorder_mod.Recorder()
        self.patches = [mock.patch.object(recorder_mod, "CAM_DIR", self.root),
                        mock.patch.object(recorder_mod.store, "event", side_effect=lambda *a: self.events.append(a)),
                        mock.patch.object(recorder_mod, "archive")]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def _seg(self, name: str, data: bytes = b"") -> Path:
        path = self.incoming / name
        path.write_bytes(data)
        old = path.stat().st_mtime - 30
        os.utime(path, (old, old))
        return path

    def test_broken_segment_is_discarded_once_with_specific_reason(self):
        seg = self._seg("seg_20261113_050000.mp4")
        with mock.patch.object(recorder_mod, "strip_audio", side_effect=SegmentError("segment_empty", seg.name)):
            self.rec._encrypt_pending(self.cam)
            self.rec._encrypt_pending(self.cam)
        self.assertFalse(seg.exists())
        self.assertEqual(len(self.events), 1)
        self.assertIn("segment_empty", self.events[0][1])
        self.assertNotIn("audio_strip_failed", self.events[0][1])

    def test_segment_still_being_written_is_skipped(self):
        first = self._seg("seg_20261113_050000.mp4", b"a")
        last = self._seg("seg_20261113_050100.mp4", b"b")
        self.rec.procs["cam1"] = {"proc": _Proc(), "sig": ""}
        seen = []
        with mock.patch.object(recorder_mod, "strip_audio", side_effect=lambda p: seen.append(p.name)):
            self.rec._encrypt_pending(self.cam)
        self.assertEqual(seen, [first.name])
        self.assertTrue(last.exists())

    def test_strip_failure_retries_then_discards_for_privacy(self):
        seg = self._seg("seg_20261113_050000.mp4", b"a")
        err = SegmentError("audio_strip_failed", "Could not find tag")
        with mock.patch.object(recorder_mod, "strip_audio", side_effect=err):
            for _ in range(recorder_mod.STRIP_RETRIES):
                self.rec._encrypt_pending(self.cam)
        self.assertFalse(seg.exists())
        self.assertEqual(len(self.events), 2)
        self.assertTrue(all("audio_strip_failed: Could not find tag" in e[1] for e in self.events))
        recorder_mod.archive.ingest.assert_not_called()


if __name__ == "__main__":
    unittest.main()
