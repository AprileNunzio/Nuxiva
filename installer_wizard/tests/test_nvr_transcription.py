import json
import os
import random
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EAR = str(ROOT / "agenti" / "percezione" / "ear")
if EAR not in sys.path:
    sys.path.insert(0, EAR)

import native_core
import nvr_scribe
import scribe_spool
from agenti.nvr import archive as archive_mod
from agenti.nvr import fuse_py, transcripts
from agenti.nvr.scribe import ScribeDispatcher
from agenti.nvr.vault import MediaVault

NATIVE = native_core.load()
READY = NATIVE is not None and hasattr(NATIVE, "nvr_fuse")
MASTER = bytes(range(32))


class FakeVoices:
    ready = True

    def embed(self, audio):
        level = float(np.abs(audio).mean()) if len(audio) else 0.0
        return np.array([1.0, 0.0, 0.0], dtype=np.float32) if level > 0.25 else np.array([0.0, 1.0, 0.1], dtype=np.float32)

    def identify(self, probe):
        return ("anna", 0.83) if probe is not None and probe[0] > 0.5 else (None, 0.1)


def fake_transcribe(audio):
    return [{"start": 0.0, "end": 1.0, "text": "il pacco è arrivato"},
            {"start": 1.0, "end": 2.0, "text": "grazie mille"},
            {"start": 2.0, "end": 3.0, "text": "a domani"}]


def pcm(seconds: int = 3) -> bytes:
    parts = [np.full(16000, 0.5), np.full(16000, 0.1), np.full(16000, 0.1)][:seconds]
    return (np.concatenate(parts) * 32767).astype("<i2").tobytes()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {"NUXIVA_NVR_SCRIBE_DIR": str(root / "spool"),
                                                "NUXIVA_NVR_SCRIBE_KEY": str(root / "scribe.key")})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()


class SpoolTest(Base):
    def test_roundtrip_binds_name_and_kind(self):
        scribe_spool.put("jobs", "cam1__seg_1", {"camera": "cam1"}, b"abc")
        self.assertEqual(scribe_spool.names("jobs"), ["cam1__seg_1"])
        raw = (scribe_spool.folder("jobs") / "cam1__seg_1.nxs").read_bytes()
        self.assertNotIn(b"cam1", raw)
        with self.assertRaises(Exception):
            scribe_spool.open_("jobs", "cam1__seg_2", raw)
        with self.assertRaises(Exception):
            scribe_spool.open_("done", "cam1__seg_1", raw)
        self.assertEqual(scribe_spool.take("jobs", "cam1__seg_1"), ({"camera": "cam1"}, b"abc"))
        self.assertEqual(scribe_spool.names("jobs"), [])
        with self.assertRaises(scribe_spool.SpoolError):
            scribe_spool.job_name("../x", "y")
        self.assertEqual(oct((Path(os.environ["NUXIVA_NVR_SCRIBE_KEY"])).stat().st_mode & 0o777), "0o600")


class EarWorkerTest(Base):
    def test_process_labels_known_and_unknown_voices(self):
        scribe_spool.put("jobs", "cam1__seg_a", {"camera": "cam1", "segment": "seg_a", "start_ms": 1000}, pcm())
        worker = nvr_scribe.NvrScribe(FakeVoices(), lambda: False, transcribe=fake_transcribe)
        worker.process("cam1__seg_a")
        header, _ = scribe_spool.take("done", "cam1__seg_a")
        turns = header["turns"]
        self.assertEqual(turns[0]["speaker"], "anna")
        self.assertIsNone(turns[1]["speaker"])
        self.assertEqual(turns[1]["voice"], "voce-1")
        self.assertEqual(turns[2]["voice"], "voce-1")
        self.assertEqual(turns[2]["start_ms"], 2000)

    def test_cluster_fallback(self):
        rows = [[1.0, 0.0], [0.95, 0.05], [0.0, 1.0], [0.1, 0.9], [-1.0, 0.0]]
        self.assertEqual(nvr_scribe.py_cluster(rows, 0.8), [0, 0, 1, 1, 2])
        with self.assertRaises(ValueError):
            nvr_scribe.py_cluster([[float("nan")]], 0.8)

    @unittest.skipUnless(READY, "nuxiva_native non installato")
    def test_cluster_parity(self):
        rnd = random.Random(3)
        for _ in range(20):
            rows = [[rnd.uniform(-1, 1) for _ in range(8)] for _ in range(rnd.randint(1, 30))]
            for thr in (0.3, 0.6, 0.9):
                self.assertEqual(list(NATIVE.nvr_cluster_voices(rows, thr)), nvr_scribe.py_cluster(rows, thr))


def utt(source, start, end, text, speaker=None, score=0.0, weight=1.0):
    return {"source": source, "start_ms": start, "end_ms": end, "text": text, "speaker": speaker,
            "speaker_score": score, "weight": weight}


CASES = [
    [utt("a", 1000, 3000, "il pacco e arrivato", "anna", 0.8), utt("b", 1100, 3100, "il pacco è arrivato"),
     utt("c", 1050, 2900, "il pacco è arrivato", "anna", 0.7), utt("a", 9000, 9500, "ciao")],
    [utt("a", 0, 1000, "accendi la luce", "marco", 0.9, 1.5), utt("b", 100, 900, "accendi luce", "anna", 0.6, 0.8)],
    [utt("a", 0, 1000, "uno"), utt("a", 500, 1500, "due"), utt("b", 2000, 2100, "  "), utt("b", 3000, 2000, "x")],
    [],
]


class FuseTest(unittest.TestCase):
    def test_python_fuse(self):
        turns = fuse_py.py_fuse(CASES[0], 0.5)
        self.assertEqual(len(turns), 2)
        self.assertEqual(turns[0]["text"], "il pacco è arrivato")
        self.assertEqual(turns[0]["speaker"], "anna")
        self.assertEqual(turns[0]["sources"], ["a", "b", "c"])

    @unittest.skipUnless(READY, "nuxiva_native non installato")
    def test_parity(self):
        for case in CASES:
            rust = json.loads(NATIVE.nvr_fuse(json.dumps(case), 0.5))
            py = fuse_py.py_fuse(case, 0.5)
            self.assertEqual(len(rust), len(py))
            for r, p in zip(rust, py):
                self.assertAlmostEqual(r.pop("agreement"), p.pop("agreement"), places=5)
                self.assertAlmostEqual(r.pop("speaker_score"), p.pop("speaker_score"), places=5)
                self.assertEqual(r, p)


class DispatcherFlowTest(Base):
    def setUp(self):
        super().setUp()
        root = Path(self.tmp.name)
        vault = MediaVault()
        vault.root = root / "vault"
        vault._master_key = lambda: MASTER
        self.archive = archive_mod.NvrArchive(vault)
        self.store = transcripts.TranscriptStore(vault)
        self.store.root = root / "tx"
        with mock.patch.object(archive_mod, "probe", return_value={"duration_ms": 60_000, "audio": True, "video": True}):
            for cam in ("cam1", "cam2"):
                raw = root / "seg_20261112_100000.mp4"
                raw.write_bytes(b"media")
                self.archive.ingest(cam, raw)
        self.start = self.archive.catalog.summary()[0]["first_ms"]

    def test_enqueue_process_collect_and_fuse(self):
        dispatcher = ScribeDispatcher(self.archive, self.store, extract=lambda media: pcm(),
                                      allowed=lambda slug: slug == "anna")
        self.assertEqual(dispatcher.enqueue(now_ms=self.start + 60_000), 2)
        self.assertEqual(dispatcher.enqueue(now_ms=self.start + 60_000), 0)
        worker = nvr_scribe.NvrScribe(FakeVoices(), lambda: False, transcribe=fake_transcribe)
        for name in scribe_spool.names("jobs"):
            worker.process(name)
        self.assertEqual(dispatcher.collect(), 2)
        data = self.store.load("cam1", "seg_20261112_100000")
        self.assertEqual(data["turns"][0]["start_ms"], self.start)
        self.assertEqual(data["turns"][0]["speaker"], "anna")
        self.assertNotIn(b"pacco", self.store.path("cam1", "seg_20261112_100000").read_bytes())
        self.assertEqual(dispatcher.candidates(self.start + 60_000), [])
        with mock.patch.object(transcripts, "store", self.store), mock.patch.object(archive_mod, "archive", self.archive):
            marks = transcripts.transcript_markers("cam1", self.start - 1, self.start + 60_000)
            self.assertEqual([m["kind"] for m in marks], ["speech"] * 3)
            fused = transcripts.room_transcript({"cam1": 1.0, "cam2": 1.0}, self.start - 1, self.start + 60_000)
        self.assertEqual(len(fused), 3)
        self.assertEqual(fused[0]["sources"], ["cam1", "cam2"])
        self.assertEqual(fused[0]["speaker"], "anna")

    def test_privacy_drops_disallowed_speaker(self):
        dispatcher = ScribeDispatcher(self.archive, self.store, extract=lambda media: pcm(), allowed=lambda slug: False)
        dispatcher.enqueue(now_ms=self.start + 60_000)
        worker = nvr_scribe.NvrScribe(FakeVoices(), lambda: False, transcribe=fake_transcribe)
        for name in scribe_spool.names("jobs"):
            worker.process(name)
        dispatcher.collect()
        turn = self.store.load("cam1", "seg_20261112_100000")["turns"][0]
        self.assertIsNone(turn["speaker"])
        self.assertEqual(turn["speaker_score"], 0.0)


if __name__ == "__main__":
    unittest.main()
