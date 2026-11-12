import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from starlette.testclient import TestClient

import native_core
from agenti.nvr import archive as archive_mod
from agenti.nvr import playback_api, ranges
from agenti.nvr.api import admin_routes
from agenti.nvr.service import nvr
from agenti.nvr.store import EventStore
from agenti.nvr.vault import MediaVault

NATIVE = native_core.load()
READY = NATIVE is not None and hasattr(NATIVE, "nvr_parse_range")
MASTER = bytes(range(32))
HEADERS = ["", "bytes=0-9", "bytes=90-", "bytes=-10", "bytes=-1000", "bytes=50-5000", "bytes=100-", "bytes=9-1",
           "bytes=0-1,4-5", "items=0-1", "bytes=-0", "bytes=a-b", "bytes=+1-2", " bytes= 3 - 4 ", "bytes=" + "9" * 30,
           "bytes=-", "bytes=0-0", "x" * 300]


class RangeTest(unittest.TestCase):
    def test_python_rules(self):
        self.assertEqual(ranges.py_parse_range("", 100), ("whole", 0, 99))
        self.assertEqual(ranges.py_parse_range("bytes=-10", 100), ("part", 90, 99))
        self.assertEqual(ranges.py_parse_range("bytes=100-", 100)[0], "invalid")
        self.assertEqual(ranges.py_parse_range("bytes=0-1,2-3", 100)[0], "invalid")

    @unittest.skipUnless(READY, "nuxiva_native non installato")
    def test_parity(self):
        for total in (0, 1, 100, 65_536 * 3):
            for header in HEADERS:
                self.assertEqual(tuple(NATIVE.nvr_parse_range(header, total)), ranges.py_parse_range(header, total),
                                 (header, total))


class PlaybackApiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        vault = MediaVault()
        vault.root = root / "vault"
        vault._master_key = lambda: MASTER
        self.archive = archive_mod.NvrArchive(vault)
        self.store = EventStore(root / "events.db")
        nvr._store = self.store
        self.patch = mock.patch.object(playback_api, "archive", self.archive)
        self.patch.start()
        self.media = {}
        with mock.patch.object(archive_mod, "probe", return_value={"duration_ms": 60_000, "audio": True, "video": True}):
            for name in ("seg_20261112_100000", "seg_20261112_100100", "seg_20261112_100500"):
                raw = root / f"{name}.mp4"
                data = random.Random(name).randbytes(150_000)
                raw.write_bytes(data)
                row = self.archive.ingest("cam1", raw)
                self.media[row["id"]] = (row, data)
        self.first = self.media["seg_20261112_100000"][0]
        from access import require_admin
        app = FastAPI()
        app.dependency_overrides[require_admin] = lambda: "admin"
        app.include_router(admin_routes)
        self.client = TestClient(app)

    def tearDown(self):
        self.patch.stop()
        self.store.close()
        self.tmp.cleanup()

    def test_range_playback_decrypts_requested_bytes(self):
        url = "/api/nvr/play/cam1/seg_20261112_100000"
        data = self.media["seg_20261112_100000"][1]
        part = self.client.get(url, headers={"Range": "bytes=65530-65600"})
        self.assertEqual(part.status_code, 206)
        self.assertEqual(part.content, data[65530:65601])
        self.assertEqual(part.headers["content-range"], f"bytes 65530-65600/{len(data)}")
        self.assertEqual(part.headers["cache-control"], "no-store")
        whole = self.client.get(url)
        self.assertEqual(whole.status_code, 200)
        self.assertEqual(whole.content, data)
        bad = self.client.get(url, headers={"Range": "bytes=999999-"})
        self.assertEqual(bad.status_code, 416)
        self.assertEqual(self.client.get("/api/nvr/play/cam1/..%2Fetc").status_code, 404)
        self.assertEqual(self.client.get("/api/nvr/play/cam1/nope").status_code, 404)

    def test_timeline_seek_jump_and_next(self):
        start = self.first["start_ms"]
        self.store.add({"id": "ev1", "at": (start + 330_000) / 1000, "camera": "Porta", "label": "person", "score": 0.9,
                        "source": "camera", "zone": "", "text": "Persona", "camera_id": "cam1"})
        tl = self.client.get("/api/nvr/timeline", params={"camera": "cam1", "from_ms": start - 1000, "to_ms": start + 900_000}).json()
        self.assertEqual(len(tl["segments"]), 3)
        self.assertEqual(len(tl["spans"]), 2)
        self.assertEqual(tl["markers"][0]["kind"], "person")
        seek = self.client.get("/api/nvr/seek", params={"camera": "cam1", "at_ms": start + 90_000}).json()
        self.assertEqual(seek["segment"]["id"], "seg_20261112_100100")
        self.assertEqual(seek["offset_ms"], 30_000)
        jump = self.client.get("/api/nvr/jump", params={"camera": "cam1", "at_ms": start}).json()
        self.assertEqual(jump["marker"]["id"], "ev1")
        self.assertEqual(jump["seek"]["segment"]["id"], "seg_20261112_100500")
        self.assertEqual(self.client.get("/api/nvr/jump", params={"camera": "cam1", "at_ms": start + 400_000}).status_code, 404)
        nxt = self.client.get("/api/nvr/next/cam1/seg_20261112_100100").json()
        self.assertEqual(nxt["id"], "seg_20261112_100500")
        self.assertEqual(self.client.get("/api/nvr/timeline", params={"camera": "cam1", "from_ms": 0, "to_ms": 10 ** 12}).status_code, 400)
        self.assertEqual(self.client.get("/api/nvr/timeline", params={"camera": "../x", "from_ms": 0, "to_ms": 10}).status_code, 400)

    def test_pin_delete_and_recordings(self):
        rec = self.client.get("/api/nvr/recordings").json()
        self.assertEqual(rec["cameras"][0]["segments"], 3)
        pinned = self.client.post("/api/nvr/segments/cam1/seg_20261112_100000/pin", json={"pinned": True})
        self.assertEqual(pinned.json()["tier"], "pinned")
        self.assertEqual(self.client.delete("/api/nvr/segments/cam1/seg_20261112_100100").status_code, 200)
        self.assertEqual(self.client.delete("/api/nvr/segments/cam1/seg_20261112_100100").status_code, 404)
        self.assertEqual(self.client.get("/api/nvr/recordings").json()["cameras"][0]["segments"], 2)


if __name__ == "__main__":
    unittest.main()
