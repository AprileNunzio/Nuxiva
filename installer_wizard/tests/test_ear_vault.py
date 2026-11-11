import asyncio
import json
import os
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path

import numpy as np

EAR = Path(__file__).resolve().parents[1] / "features" / "ear"
if str(EAR) not in sys.path:
    sys.path.append(str(EAR))

_orig_stt = sys.modules.get("stt")
fake_stt = types.ModuleType("stt")
fake_stt.lock = asyncio.Lock()


def fake_transcribe(audio, name="same", offset=0.0):
    return [{"start": round(offset + 0.1, 2), "end": round(offset + 1.5, 2), "text": "Jarvis come va"}]


fake_stt.transcribe_segments = fake_transcribe
sys.modules["stt"] = fake_stt

import recorder
import reviewer as reviewer_module
from features.sentinel import memory_people


class EarVaultTest(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        if _orig_stt is not None:
            sys.modules["stt"] = _orig_stt
        else:
            sys.modules.pop("stt", None)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        recorder.ROOT = self.root
        recorder.RECORDS = self.root / "chunks"
        reviewer_module.REVIEWS = self.root / "reviews.jsonl"
        reviewer_module.SUMMARY = self.root / "summary.json"
        self.rng = np.random.default_rng(42)

    def tearDown(self):
        self.tmp.cleanup()

    def make_chunk(self, chunk_id="test12345678"):
        audio = (self.rng.standard_normal(recorder.RATE * 2) * 0.05).astype(np.float32)
        meta = {
            "id": chunk_id[:12],
            "source": "desk_mic",
            "started": time.time() - 30.0,
            "duration": 2.0,
            "voiced_s": 1.8,
            "layout": [[0.0, 0.0, 2.0]],
            "events": [{"kind": "wake", "t": 0.5}],
            "reviewed": False,
        }
        return recorder.Chunk(meta, audio)

    def test_encrypted_chunk_write_and_read(self):
        chunk = self.make_chunk()
        recorder.write_chunk(chunk, encrypt=True)
        files = recorder.listing()
        self.assertEqual(len(files), 1)
        meta_file, meta = files[0]
        self.assertTrue(meta.get("encrypted"))
        self.assertTrue(meta_file.with_suffix(".nvm").exists())
        self.assertFalse(meta_file.with_suffix(".wav").exists())
        recovered = recorder.read_chunk_audio(meta_file, meta)
        self.assertEqual(len(recovered), len(chunk.audio))
        diff = np.abs(recovered - np.clip(chunk.audio, -1, 1))
        self.assertLess(float(np.max(diff)), 1e-4)

    def test_encrypted_chunk_remove_and_purge(self):
        chunk = self.make_chunk("purge1234567")
        recorder.write_chunk(chunk, encrypt=True)
        meta_file, _ = recorder.listing()[0]
        recorder.remove(meta_file)
        self.assertEqual(recorder.listing(), [])
        self.assertFalse(meta_file.with_suffix(".nvm").exists())

    def test_encrypted_chunk_prune(self):
        chunk = self.make_chunk("prune1234567")
        recorder.write_chunk(chunk, encrypt=True)
        meta_file, meta = recorder.listing()[0]
        meta["started"] = time.time() - 86400 * 2
        meta_file.write_text(json.dumps(meta), encoding="utf-8")
        os.environ["NUXIVA_EAR_RECORD_HOURS"] = "1"
        try:
            removed = recorder.prune()
            self.assertEqual(removed, 1)
            self.assertEqual(recorder.listing(), [])
        finally:
            os.environ.pop("NUXIVA_EAR_RECORD_HOURS", None)

    def test_review_encrypted_chunk_and_indexing(self):
        chunk = self.make_chunk("revchunk1234")
        recorder.write_chunk(chunk, encrypt=True)
        rv = reviewer_module.Reviewer(lambda: False)
        reviewer_module.activity.last_voice = time.time() - 500
        meta_file, meta = recorder.listing()[0]
        asyncio.run(rv.review(meta_file, meta))
        self.assertTrue(meta.get("reviewed"))
        rows = reviewer_module.recent_reviews(5)
        self.assertEqual(len(rows), 1)
        self.assertIn("review_text", rows[0])

    def test_allows_voice_consent(self):
        self.assertTrue(memory_people.allows_voice(None))
        self.assertTrue(memory_people.allows_voice({"consent": True, "consent_voice": True}))
        self.assertFalse(memory_people.allows_voice({"consent": False}))
        self.assertFalse(memory_people.allows_voice({"consent": True, "consent_voice": False}))

    def test_journal_audio_playback_audit(self):
        from unittest import mock
        from features.ear.journal import journal
        from features.ear.journal_api import routes
        import features.ear.journal_api as journal_api
        from starlette.testclient import TestClient
        from fastapi import FastAPI
        journal.root = self.root / "journal"
        journal.ready = False
        app = FastAPI()
        app.include_router(routes)
        client = TestClient(app)
        audio = (self.rng.standard_normal(recorder.RATE) * 0.05).astype(np.float32)
        entry_id = journal.record("heard", "test phrase", audio=audio)
        self.assertTrue(bool(entry_id))
        with mock.patch.object(journal_api, "require_admin"):
            resp = client.get(f"/api/ear/journal/{entry_id}/audio")
        self.assertEqual(resp.status_code, 200)
        self.assertGreater(len(resp.content), 0)


if __name__ == "__main__":
    unittest.main()
