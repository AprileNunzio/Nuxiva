import shutil
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from agenti.particles import ParticleStore, archive, codec

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "RustCreationArchive")
SPEC = {"parts": [{"shape": "sphere", "size": [1, 1, 1], "at": [0, 0, 0], "rot": [0, 0, 0], "color": "#ffffff", "weight": 1.0}]}


def digest(n: int) -> str:
    return f"{n:08x}" * 8


def entry(key: str, n: int, tags=()) -> dict:
    return {"key": key, "digest": digest(n), "kind": "particles", "meta": "{}", "tags": list(tags)}


def engines(root: Path):
    found = {"python": archive.open_archive(root / "py.db", native=False)}
    if NATIVE:
        found["rust"] = archive.open_archive(root / "rs.db", native=True)
    return found


class ArchiveTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)

    def test_engines_give_the_same_answers(self):
        script = [("put", entry("medusa lunare", 1, ["animale", "mare"]), 1), ("put", entry("medusa cassiopea", 2, ["animale"]), 2),
                  ("put", entry("motore v8", 3, ["auto"]), 3), ("lookup", "medusa cassiopea", 5), ("put", entry("medusa lunare", 4, ["animale"]), 6),
                  ("lookup", "assente", 7)]
        results = {}
        for name, engine in engines(self.root).items():
            log = []
            for op, arg, now in script:
                log.append(getattr(engine, op)(arg, now))
            log.append([engine.search(q, 10) for q in ("medus", "animale", "auto v8", "zzz", "", "meccanica")])
            log.append(engine.recent(10))
            log.append(engine.count())
            log.append(engine.evict(2))
            log.append(engine.count())
            results[name] = log
        if NATIVE:
            self.assertEqual(results["python"], results["rust"])
        self.assertEqual(results["python"][-1], 2)

    def test_hostile_queries_and_entries(self):
        for name, engine in engines(self.root).items():
            with self.subTest(name):
                engine.put(entry("medusa", 1), 1)
                for query in ('"', "*", 'medusa" OR "x', "NEAR(a b)", "a) OR (b", "'; DROP TABLE creations; --", "key:medusa", "-medusa", "a" * 10_000):
                    engine.search(query, 5)
                self.assertEqual(engine.count(), 1)
                for bad in ({**entry("k", 1), "key": ""}, {**entry("k", 1), "key": "x" * 121}, {**entry("k", 1), "digest": "../" * 30},
                            {**entry("k", 1), "digest": "A" * 64}, {**entry("k", 1), "kind": ""}, {**entry("k", 1), "meta": "x" * 20_000}):
                    with self.assertRaises(ValueError):
                        engine.put(bad, 1)

    def test_shard_and_tokens(self):
        self.assertEqual(archive.shard(digest(0xabcdef01)), f"ab/cd/{digest(0xabcdef01)}")
        for bad in ("", "A" * 64, "g" * 64, "../" + "a" * 61, None):
            self.assertIsNone(archive.shard(bad))
        self.assertEqual(archive.tokens("Medusa, MEDUSA! città-stato"), ["medusa", "città", "stato"])
        if NATIVE:
            self.assertEqual(nuxiva_native.creations_tokens("Medusa, MEDUSA! città_stato", 8), archive.tokens("Medusa, MEDUSA! città_stato", 8))
            self.assertEqual(nuxiva_native.creations_shard(digest(7)), archive.shard(digest(7)))

    def test_many_creations_stay_searchable_fast(self):
        engine = archive.open_archive(self.root / "grande.db")
        conn_rows = [(f"oggetto {n % 997} {n}", digest(n)) for n in range(20_000)]
        started = time.monotonic()
        for key, dig in conn_rows:
            engine.put({"key": key, "digest": dig, "kind": "particles", "meta": "{}", "tags": ["forma"]}, 1)
        self.assertLess(time.monotonic() - started, 60)
        started = time.monotonic()
        for _ in range(100):
            self.assertTrue(engine.search("ogget 42", 10))
            self.assertIsNotNone(engine.lookup("oggetto 42 42", 2))
        self.assertLess(time.monotonic() - started, 10)
        self.assertEqual(engine.count(), 20_000)


class StoreArchiveTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)

    def blob(self, seed: int) -> bytes:
        return codec.sample_python(SPEC, 256, seed)

    def test_blobs_are_sharded_and_legacy_blobs_still_load(self):
        store = ParticleStore(self.root)
        blob = self.blob(1)
        saved = store.put("palla", SPEC, blob)
        self.assertTrue((self.root / "blobs" / archive.shard(saved["digest"])).with_suffix(".nxpc").is_file())
        legacy = self.blob(2)
        import hashlib
        dig = hashlib.sha256(legacy).hexdigest()
        (self.root / "blobs" / f"{dig}.nxpc").write_bytes(legacy)
        self.assertEqual(ParticleStore(self.root).blob(dig), legacy)

    def test_creations_beyond_the_hot_index_are_restored_from_the_archive(self):
        with mock.patch("agenti.particles.store.MAX_CONCEPTS", 3):
            store = ParticleStore(self.root)
            for n in range(8):
                store.put(f"forma {n}", SPEC, self.blob(n))
            self.assertLessEqual(len(store.index), 3)
            fresh = ParticleStore(self.root)
            self.assertEqual(fresh.count(), 8)
            for n in range(8):
                found = fresh.lookup(f"forma {n}")
                self.assertIsNotNone(found, n)
                self.assertEqual(fresh.blob(found["digest"]), self.blob(n))

    def test_search_finds_creations_by_word_and_prefix(self):
        store = ParticleStore(self.root)
        store.put("medusa lunare", SPEC, self.blob(1), ["animale"])
        store.put("motore v8", SPEC, self.blob(2), ["auto"])
        self.assertEqual([h["key"] for h in store.search("medus")], ["medusa lunare"])
        self.assertEqual([h["key"] for h in store.search("auto")], ["motore v8"])
        self.assertEqual(store.search("zzz"), [])

    def test_tampered_archive_rows_are_ignored(self):
        store = ParticleStore(self.root)
        saved = store.put("ruota", SPEC, self.blob(1))
        other = store.put("vite", SPEC, self.blob(2))
        (self.root / "index.json").unlink()
        del store
        conn = sqlite3.connect(self.root / "creazioni.db")
        conn.execute("UPDATE creations SET digest = ? WHERE key = 'ruota'", (other["digest"],))
        conn.commit()
        conn.close()
        fresh = ParticleStore(self.root)
        self.assertIsNone(fresh.lookup("ruota"))
        self.assertIsNotNone(saved)

    def test_a_legacy_index_is_migrated_into_the_archive(self):
        store = ParticleStore(self.root)
        store.put("antica", SPEC, self.blob(1))
        (self.root / "creazioni.db").unlink()
        for suffix in ("-wal", "-shm"):
            (self.root / f"creazioni.db{suffix}").unlink(missing_ok=True)
        fresh = ParticleStore(self.root)
        self.assertEqual(fresh.count(), 1)
        self.assertEqual([h["key"] for h in fresh.search("antica")], ["antica"])

    def test_old_blobs_are_removed_when_the_archive_overflows(self):
        with mock.patch("agenti.particles.store.MAX_ARCHIVE", 4), mock.patch("agenti.particles.store.EVICT_EVERY", 1):
            store = ParticleStore(self.root)
            saved = []
            for n in range(6):
                saved.append(store.put(f"vecchia {n}", SPEC, self.blob(n)))
                time.sleep(0.003)
            self.assertEqual(store.count(), 4)
            files = {p.stem for p in (self.root / "blobs").rglob("*.nxpc")}
            self.assertEqual(files, {s["digest"] for s in saved[2:]})


if __name__ == "__main__":
    unittest.main()
