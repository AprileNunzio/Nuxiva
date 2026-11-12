import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from starlette.testclient import TestClient

import native_core
from agenti.nvr import archive as archive_mod
from agenti.nvr import find_api, index_py, search_index, transcripts
from agenti.nvr.api import admin_routes
from agenti.nvr.search import has_time, speech_terms
from agenti.nvr.service import nvr
from agenti.nvr.store import EventStore
from agenti.nvr.vault import MediaVault

NATIVE = native_core.load()
READY = NATIVE is not None and hasattr(NATIVE, "RustNvrIndex")
MASTER = bytes(range(32))
KEY = search_index.index_key(MASTER)
WORDS = ["pacco", "arrivato", "chiavi", "cucina", "porta", "grazie", "domani", "Perché", "città", "luce", "accendi",
         "ciao", "x", "andiamo", "andare", "àncora", "ÉCOLE", "über", "naïve", "1234", "a1b2", "!!", "—"]


def doc(rnd: random.Random, i: int) -> tuple[str, str]:
    meta = {"key": f"cam{i % 3}|seg_{i // 4}|{i * 1000}", "camera": f"cam{i % 3}", "at_ms": i * 1000, "kind": "speech"}
    return json.dumps(meta), " ".join(rnd.choice(WORDS) for _ in range(rnd.randint(0, 12)))


QUERIES = ["pacco", "pac", "pacc", "arriv chiavi", "PERCHE", "citta", "and", "anda", "ancora", "ecole", "uber", "naive",
           "1234", "", "!!", "zzz", "porta cucina luce", "a1b2 ciao"]


class IndexParityTest(unittest.TestCase):
    def test_python_semantics(self):
        idx = index_py.PyNvrIndex(KEY)
        idx.add(json.dumps({"key": "a|s|1", "camera": "a", "at_ms": 1, "kind": "speech"}), "Il pacco è arrivato in cucina")
        idx.add(json.dumps({"key": "b|s|2", "camera": "b", "at_ms": 2, "kind": "speech"}), "le chiavi sono in cucina")
        self.assertEqual([h["key"] for h in json.loads(idx.search("cucina", None, 0, 10, 10))], ["b|s|2", "a|s|1"])
        self.assertEqual([h["key"] for h in json.loads(idx.search("pacc cucina", None, 0, 10, 10))], ["a|s|1"])
        self.assertEqual(json.loads(idx.search("cucina", "b", 0, 10, 10))[0]["camera"], "b")
        self.assertEqual(json.loads(idx.search("cucina", None, 2, 10, 10))[0]["key"], "b|s|2")
        self.assertEqual(idx.remove_prefix("a|s|"), 1)
        self.assertEqual(json.loads(idx.search("pacco", None, 0, 10, 10)), [])
        blob = idx.to_json()
        self.assertNotIn("pacco", blob)
        self.assertNotIn("cucina", blob)
        with self.assertRaises(ValueError):
            index_py.PyNvrIndex(b"short")

    @unittest.skipUnless(READY, "nuxiva_native non installato")
    def test_parity(self):
        rnd = random.Random(11)
        rust, py = NATIVE.RustNvrIndex(KEY), index_py.PyNvrIndex(KEY)
        for i in range(60):
            meta, text = doc(rnd, i)
            rust.add(meta, text)
            py.add(meta, text)
        for prefix in ("cam1|seg_2|", "cam0|seg_9|", "nothing|"):
            self.assertEqual(rust.remove_prefix(prefix), py.remove_prefix(prefix))
        meta, text = doc(rnd, 5)
        rust.add(meta, "sostituito pacco")
        py.add(meta, "sostituito pacco")
        self.assertEqual(json.loads(rust.to_json()), json.loads(py.to_json()))
        for q in QUERIES:
            for camera in (None, "cam1"):
                self.assertEqual(json.loads(rust.search(q, camera, 0, 50_000, 20)),
                                 json.loads(py.search(q, camera, 0, 50_000, 20)), (q, camera))
        clone = NATIVE.RustNvrIndex.from_json(KEY, py.to_json())
        self.assertEqual(json.loads(clone.search("pacco", None, 0, 10**9, 5)), json.loads(py.search("pacco", None, 0, 10**9, 5)))

    def test_query_helpers(self):
        self.assertEqual(speech_terms("cosa ha detto Anna ieri sul pacco?"), "ha detto anna pacco")
        self.assertTrue(has_time("pacco ieri"))
        self.assertFalse(has_time("pacco"))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.vault = MediaVault()
        self.vault.root = root / "vault"
        self.vault._master_key = lambda: MASTER
        self.archive = archive_mod.NvrArchive(self.vault)
        self.tx = transcripts.TranscriptStore(self.vault)
        self.tx.root = root / "tx"
        self.index = search_index.SearchIndex(self.vault, self.tx)
        self.archive.listeners.append(search_index.forget_derived(self.tx, self.index))
        with mock.patch.object(archive_mod, "probe", return_value={"duration_ms": 60_000, "audio": True, "video": True}):
            for cam in ("cam1", "cam2"):
                raw = root / "seg_20261112_100000.mp4"
                raw.write_bytes(b"media")
                self.archive.ingest(cam, raw)
        self.start = self.archive.catalog.get("cam1", "seg_20261112_100000")["start_ms"]
        for cam, text in (("cam1", "il pacco è arrivato davanti alla porta"), ("cam2", "le chiavi sono in cucina")):
            turns = [{"start_ms": self.start + 1000, "end_ms": self.start + 3000, "text": text, "speaker": "anna",
                      "speaker_score": 0.8, "voice": None}]
            self.tx.save(cam, "seg_20261112_100000", {"camera": cam, "segment": "seg_20261112_100000",
                                                       "start_ms": self.start, "turns": turns})
            self.index.index_transcript(cam, "seg_20261112_100000", turns)

    def tearDown(self):
        self.tmp.cleanup()


class SearchIndexTest(Base):
    def test_search_persist_and_rebuild(self):
        hits = self.index.search("pacco", None, 0, 10**13)
        self.assertEqual([h["camera"] for h in hits], ["cam1"])
        self.index.save(force=True)
        raw = self.index.path.read_bytes()
        self.assertNotIn(b"pacco", raw)
        self.assertNotIn(b"cam1", raw)
        again = search_index.SearchIndex(self.vault, self.tx)
        self.assertEqual(again.search("chiav", None, 0, 10**13)[0]["camera"], "cam2")
        self.index.path.write_bytes(raw[:-3] + b"xyz")
        rebuilt = search_index.SearchIndex(self.vault, self.tx)
        self.assertEqual(rebuilt.search("porta", "cam1", 0, 10**13)[0]["at_ms"], self.start + 1000)
        self.index.path.unlink()
        self.assertEqual(len(search_index.SearchIndex(self.vault, self.tx).search("anna", None, 0, 10**13)), 2)

    def test_delete_segment_forgets_transcript_and_index(self):
        self.assertTrue(self.archive.delete("cam1", "seg_20261112_100000"))
        self.assertFalse(self.tx.exists("cam1", "seg_20261112_100000"))
        self.assertEqual(self.index.search("pacco", None, 0, 10**13), [])
        self.assertEqual(len(self.index.search("chiavi", None, 0, 10**13)), 1)


class FindApiTest(Base):
    def setUp(self):
        super().setUp()
        self.store = EventStore(Path(self.tmp.name) / "events.db")
        nvr._store = self.store
        self.store.add({"id": "e1", "at": (self.start + 20_000) / 1000, "camera": "Ingresso", "label": "package",
                        "score": 0.9, "text": "pacco sul tappeto", "camera_id": "cam1"})
        self.store.add({"id": "e2", "at": (self.start + 30_000) / 1000, "camera": "Cucina", "label": "person",
                        "score": 0.8, "text": "", "camera_id": "cam2"})
        self.patches = [mock.patch.object(find_api, "archive", self.archive),
                        mock.patch.object(search_index, "index", self.index),
                        mock.patch.object(find_api, "people_names", lambda: {"anna": "Anna"}),
                        mock.patch.object(find_api, "camera_names", lambda: {"cam1": {"name": "Ingresso", "room": ""}})]
        for p in self.patches:
            p.start()
        from access import require_admin
        app = FastAPI()
        app.dependency_overrides[require_admin] = lambda: "admin"
        app.include_router(admin_routes)
        self.client = TestClient(app)

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.store.close()
        super().tearDown()

    def test_find_speech_and_events(self):
        data = find_api.find("pacco", None, 20, now_ms=self.start + 3_600_000)
        self.assertEqual(len(data["speech"]), 1)
        speech = data["speech"][0]
        self.assertEqual((speech["camera"], speech["segment"], speech["speaker_name"]), ("cam1", "seg_20261112_100000", "Anna"))
        self.assertIn("pacco", speech["text"])
        self.assertEqual([(e["kind"], e["segment"]) for e in data["events"]], [("package", "seg_20261112_100000")])
        only = find_api.find("persona", "cam1", 20, now_ms=self.start + 3_600_000)
        self.assertEqual(only["events"], [])

    def test_routes(self):
        self.assertEqual(self.client.get("/api/nvr/find", params={"q": "   "}).status_code, 400)
        self.assertEqual(self.client.get("/api/nvr/find", params={"q": "pacco", "camera": "../x"}).status_code, 400)
        res = self.client.get("/api/nvr/find", params={"q": "chiavi", "camera": "cam2"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual([h["camera"] for h in res.json()["speech"]], ["cam2"])
        seg = self.client.get("/api/nvr/segments/cam2/seg_20261112_100000/events").json()
        self.assertEqual([i["kind"] for i in seg["items"]], ["speech", "person"])
        self.assertEqual(self.client.get("/api/nvr/segments/cam2/seg_missing/events").status_code, 404)


if __name__ == "__main__":
    unittest.main()
