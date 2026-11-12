import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import native_core
from agenti.nvr import archive as archive_mod
from agenti.nvr import catalog as catalog_mod
from agenti.nvr import catalog_py, nvm2, xchacha
from agenti.nvr.vault import MediaVault

NATIVE = native_core.load()
READY = NATIVE is not None and hasattr(NATIVE, "RustNvrCatalog") and hasattr(getattr(NATIVE, "RustMediaVault", None), "seal_v2")
MASTER = bytes(range(32))
NONCE = bytes(range(100, 124))
ARGS = ("cam-door", "2026-11-12", "seg_20261112_101500", 1_794_478_500_000, 60_000, True, True, "continuous")


def media(size: int) -> bytes:
    rnd = random.Random(size)
    return bytes(rnd.getrandbits(8) for _ in range(size))


class XChaChaTest(unittest.TestCase):
    def test_hchacha20_reference_vector(self):
        key = bytes(range(32))
        nonce = bytes.fromhex("000000090000004a0000000031415927")
        self.assertEqual(xchacha.hchacha20(key, nonce).hex(),
                         "82413b4227b27bfed30e42508a877d73a0f9e4d58a74a853c12ec41326d3ecdc")

    def test_seal_open_and_reject_tamper(self):
        sealed = xchacha.seal(MASTER, NONCE, b"ciao", b"aad")
        self.assertEqual(xchacha.open_(MASTER, NONCE, sealed, b"aad"), b"ciao")
        with self.assertRaises(Exception):
            xchacha.open_(MASTER, NONCE, sealed, b"other")


class PythonFormatTest(unittest.TestCase):
    def test_roundtrip_range_and_tamper(self):
        raw = media(nvm2.CHUNK_SIZE * 2 + 333)
        sealed = nvm2.py_seal(MASTER, *ARGS, NONCE, raw)
        header, plain = nvm2.py_open(MASTER, sealed)
        self.assertEqual(plain, raw)
        self.assertEqual(header["chunk_count"], 3)
        forged = sealed.replace(b'"continuous"', b'"pinned"    ', 1)
        with self.assertRaises(Exception):
            nvm2.py_open(MASTER, forged)
        with self.assertRaises(Exception):
            nvm2.py_open(MASTER, sealed[:-1])
        with self.assertRaises(Exception):
            nvm2.py_open(bytes(32), sealed)

    def test_hostile_ids_rejected(self):
        with self.assertRaises(nvm2.FormatError):
            nvm2.py_seal(MASTER, "../x", *ARGS[1:], NONCE, b"x")
        self.assertIsNone(nvm2.chunk_span(0, 0, 0))
        self.assertEqual(nvm2.chunk_span(nvm2.CHUNK_SIZE * 3, 5, 10 ** 12), (0, 2))


@unittest.skipUnless(READY, "nuxiva_native non installato")
class VaultParityTest(unittest.TestCase):
    def setUp(self):
        self.engine = NATIVE.RustMediaVault(MASTER)

    def test_identical_bytes_both_directions(self):
        for size in (0, 1, nvm2.CHUNK_SIZE, nvm2.CHUNK_SIZE * 2 + 77):
            raw = media(size)
            rust = bytes(self.engine.seal_v2(*ARGS, NONCE, raw))
            py = nvm2.py_seal(MASTER, *ARGS, NONCE, raw)
            self.assertEqual(rust, py)
            self.assertEqual(nvm2.py_open(MASTER, rust)[1], raw)
            text, plain = self.engine.open_v2(py)
            self.assertEqual(bytes(plain), raw)
            self.assertEqual(json.loads(text), nvm2.py_header(py)[0])

    def test_chunk_access_and_blob(self):
        raw = media(nvm2.CHUNK_SIZE * 3 + 5)
        sealed = nvm2.py_seal(MASTER, *ARGS, NONCE, raw)
        header, _, start = nvm2.py_header(sealed)
        for index in range(header["chunk_count"]):
            at = nvm2.frame_offset(start, index)
            frame = sealed[at:at + nvm2.frame_len(header, index)]
            self.assertEqual(bytes(self.engine.open_chunk_v2(sealed[:start], index, frame)),
                             nvm2.py_open_chunk(MASTER, sealed[:start], index, frame))
        for span in ((0, 0), (65535, 65536), (5, 10 ** 9), (10 ** 9, 10 ** 9 + 1)):
            self.assertEqual(NATIVE.nvr_chunk_span(len(raw), *span), nvm2.chunk_span(len(raw), *span))
        blob = bytes(self.engine.seal_blob("nvr.catalog.v1", NONCE, b"[1,2]"))
        self.assertEqual(blob, nvm2.py_seal_blob(MASTER, "nvr.catalog.v1", NONCE, b"[1,2]"))
        self.assertEqual(nvm2.py_open_blob(MASTER, "nvr.catalog.v1", blob), b"[1,2]")
        with self.assertRaises(ValueError):
            self.engine.open_blob("nvr.other", blob)


def segment(camera: str, i: int, rnd: random.Random) -> dict:
    return {"id": f"s{i}", "camera": camera, "start_ms": i * 60_000 + rnd.randint(0, 5000),
            "duration_ms": rnd.choice([30_000, 60_000]), "bytes": rnd.randint(100, 5000),
            "tier": rnd.choice(["continuous", "continuous", "event", "pinned"]), "audio": rnd.random() > 0.3,
            "video": True}


@unittest.skipUnless(READY, "nuxiva_native non installato")
class CatalogParityTest(unittest.TestCase):
    def test_random_operations_match(self):
        rnd = random.Random(7)
        rust, py = NATIVE.RustNvrCatalog(), catalog_py.PyNvrCatalog()
        for camera in ("cam-a", "cam-b"):
            for i in range(150):
                row = json.dumps(segment(camera, i, rnd))
                rust.insert(row)
                py.insert(row)
        for i in range(0, 150, 7):
            self.assertEqual(rust.remove("cam-a", f"s{i}"), py.remove("cam-a", f"s{i}"))
        rust.set_tier("cam-b", "s3", "pinned")
        py.set_tier("cam-b", "s3", "pinned")
        self.assertEqual(len(rust), len(py))
        self.assertEqual(json.loads(rust.to_json()), json.loads(py.to_json()))
        self.assertEqual(json.loads(rust.summary()), json.loads(py.summary()))
        for _ in range(60):
            camera = rnd.choice(["cam-a", "cam-b", "cam-z"])
            a, b = sorted(rnd.randint(0, 9_500_000) for _ in range(2))
            self.assertEqual(json.loads(rust.range(camera, a, b, 40)), json.loads(py.range(camera, a, b, 40)))
            self.assertEqual(json.loads(rust.spans(camera, a, b, 3000)), json.loads(py.spans(camera, a, b, 3000)))
            got_r, got_p = rust.seek(camera, a), py.seek(camera, a)
            self.assertEqual(json.loads(got_r) if got_r else None, json.loads(got_p) if got_p else None)
        events = json.dumps([["cam-a", 600_000], ["cam-b", 3_000_000], ["cam-b", 8_000_000]])
        for quota in (0, 200_000, 50_000):
            policy = json.dumps({"continuous_ms": 2_000_000, "event_ms": 7_000_000, "quota_bytes": quota,
                                 "event_pad_ms": 30_000, "continuous_overrides": {"cam-b": 4_000_000}})
            self.assertEqual(json.loads(rust.plan(policy, events, 9_500_000)), json.loads(py.plan(policy, events, 9_500_000)))
        with self.assertRaises(ValueError):
            rust.range("../etc", 0, 10, 5)
        with self.assertRaises(ValueError):
            py.range("../etc", 0, 10, 5)

    def test_markers_match(self):
        markers = [{"at_ms": t, "camera": "cam-a", "kind": k, "id": f"m{t}", "label": "", "score": 0.5}
                   for t, k in ((100, "person"), (500, "speech"), (900, "person"), (900, "car"))]
        text = json.dumps(markers)
        for at, forward, kinds in ((100, True, []), (100, True, ["person"]), (900, False, []), (900, True, []), (0, True, ["car"])):
            r = NATIVE.nvr_next_marker(text, at, forward, kinds)
            p = catalog_py.next_marker(text, at, forward, kinds)
            self.assertEqual(json.loads(r) if r else None, json.loads(p) if p else None)


class ArchiveFlowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = MediaVault()
        self.vault.root = Path(self.tmp.name) / "vault"
        self.vault._master_key = lambda: MASTER
        self.archive = archive_mod.NvrArchive(self.vault)

    def tearDown(self):
        self.tmp.cleanup()

    def _raw(self, name: str, size: int = 70_000) -> Path:
        path = Path(self.tmp.name) / name
        path.write_bytes(media(size))
        return path

    def test_ingest_seek_read_range_and_maintain(self):
        with mock.patch.object(archive_mod, "probe", return_value={"duration_ms": 60_000, "audio": True, "video": True}):
            first = self.archive.ingest("cam1", self._raw("seg_20261112_100000.mp4"))
            second = self.archive.ingest("cam1", self._raw("seg_20261112_100100.mp4"))
        self.assertEqual(second["start_ms"] - first["start_ms"], 60_000)
        seek = self.archive.catalog.seek("cam1", first["start_ms"] + 61_500)
        self.assertEqual(seek["segment"]["id"], second["id"])
        self.assertEqual(seek["offset_ms"], 1500)
        path = self.vault.path_for("cam1", first["id"])
        whole = self.vault.decrypt_file("cam1", path)
        self.assertEqual(b"".join(self.vault.read_range("cam1", path, 65_530, 65_545)), whole[65_530:65_546])
        self.assertEqual(b"".join(self.vault.stream_chunks("cam1", path)), whole)
        self.archive.pin("cam1", first["id"], True)
        now = second["start_ms"] + 10 * 86_400_000
        done = self.archive.maintain([], {"continuous_hours": 1, "retention_days": 3, "storage_percent": 20,
                                          "storage_max_gb": 0}, {}, now_ms=now)
        self.assertEqual(done["expired"], 1)
        self.assertTrue(path.exists())
        self.assertFalse(self.vault.path_for("cam1", second["id"]).exists())

    def test_catalog_survives_restart_and_rebuilds(self):
        with mock.patch.object(archive_mod, "probe", return_value={"duration_ms": 30_000, "audio": False, "video": True}):
            row = self.archive.ingest("cam2", self._raw("seg_20261112_110000.mp4", 10))
        self.archive.pin("cam2", row["id"], True)
        blob = (self.vault.root / catalog_mod.FILE_NAME).read_bytes()
        self.assertNotIn(b"cam2", blob)
        fresh = archive_mod.NvrArchive(self.vault)
        self.assertEqual(fresh.catalog.get("cam2", row["id"])["tier"], "pinned")
        (self.vault.root / catalog_mod.FILE_NAME).unlink()
        rebuilt = archive_mod.NvrArchive(self.vault)
        self.assertEqual(rebuilt.catalog.get("cam2", row["id"])["duration_ms"], 30_000)
        self.assertFalse(rebuilt.catalog.get("cam2", row["id"])["audio"])


if __name__ == "__main__":
    unittest.main()
