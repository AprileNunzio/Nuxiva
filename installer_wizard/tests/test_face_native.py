import sys
import unittest
from pathlib import Path

import numpy as np

BIO = Path(__file__).resolve().parents[1] / "features" / "biometrics"
if str(BIO) not in sys.path:
    sys.path.append(str(BIO))

import embeddings as emb
import face_engine

NATIVE = face_engine.native_class()
DIM = 128


def person(seed: int, n: int, noise: float) -> np.ndarray:
    rng = np.random.default_rng(seed)
    base = emb.unit(rng.standard_normal(DIM))
    return emb.unit_rows(base + rng.standard_normal((n, DIM)) * noise / np.sqrt(DIM) * 4)


def probes(rows: np.ndarray, seed: int, count: int, noise: float) -> list:
    rng = np.random.default_rng(seed)
    c = emb.centroid(rows)
    return [emb.unit(c + rng.standard_normal(DIM) * noise / np.sqrt(DIM) * 4) for _ in range(count)]


def scenario() -> list:
    owner = person(1, 30, 0.35)
    twin_base = emb.unit(emb.centroid(owner) * 0.55 + emb.unit(np.random.default_rng(9).standard_normal(DIM)) * 0.55)
    twin = emb.unit_rows(twin_base + np.random.default_rng(10).standard_normal((20, DIM)) * 0.35 / np.sqrt(DIM) * 4)
    return [("nunzio", owner, None, False), ("ospite-1", person(1, 12, 0.4), None, True),
            ("anna", person(2, 25, 0.35), None, False), ("gemello", twin, None, False),
            ("frame-dup", emb.unit_rows(np.repeat(person(3, 1, 0.0), 30, axis=0) + 1e-4), None, False)]


class PythonEngineTest(unittest.TestCase):
    def setUp(self):
        self.book = face_engine.PyFaceBook(face_engine.Settings())
        self.book.replace(scenario())

    def test_duplicate_frames_keep_the_base_threshold(self):
        report = {r["slug"]: r for r in self.book.report()}
        self.assertAlmostEqual(report["frame-dup"]["threshold"], 0.40, places=5)
        self.assertLessEqual(report["nunzio"]["threshold"], 0.40)

    def test_owner_shadow_is_found_and_owner_wins(self):
        self.assertEqual([(g, h) for g, h, _ in self.book.shadows()], [("ospite-1", "nunzio")])
        owner = scenario()[0][1]
        hits = [self.book.verdict(p)["slug"] for p in probes(owner, 4, 20, 0.3)]
        self.assertGreaterEqual(hits.count("nunzio"), 15)
        self.assertNotIn("ospite-1", hits)

    def test_strangers_stay_unknown(self):
        stranger = person(77, 10, 0.3)
        self.assertTrue(all(self.book.verdict(p)["slug"] is None for p in probes(stranger, 5, 10, 0.3)))


@unittest.skipIf(NATIVE is None, "modulo Rust nuxiva_native non installato")
class NativeParityTest(unittest.TestCase):
    def setUp(self):
        settings = face_engine.Settings()
        self.py = face_engine.PyFaceBook(settings)
        self.rs = face_engine.NativeFaceBook(NATIVE, settings)
        for book in (self.py, self.rs):
            book.replace(scenario())

    def test_reports_match(self):
        py = {r["slug"]: r for r in self.py.report()}
        rs = {r["slug"]: r for r in self.rs.report()}
        self.assertEqual(set(py), set(rs))
        for slug in py:
            self.assertAlmostEqual(py[slug]["threshold"], rs[slug]["threshold"], places=4)
            self.assertEqual(py[slug]["shadow_of"], rs[slug]["shadow_of"])
            self.assertEqual([s for s, _ in py[slug]["similar"]], [s for s, _ in rs[slug]["similar"]])

    def test_verdicts_match_on_many_probes(self):
        for i, (_, rows, _, _) in enumerate(scenario()):
            for probe in probes(rows, 100 + i, 15, 0.45):
                a, b = self.py.verdict(probe), self.rs.verdict(probe)
                self.assertEqual((a["slug"], a["best"], a["ambiguous"], a["twin"], a["reason"]),
                                 (b["slug"], b["best"], b["ambiguous"], b["twin"], b["reason"]))
                self.assertAlmostEqual(a["score"], b["score"], places=4)
                self.assertEqual(self.py.may_learn("nunzio", probe), self.rs.may_learn("nunzio", probe))

    def test_closest_and_centroid_scores_match(self):
        probe = probes(scenario()[2][1], 3, 1, 0.3)[0]
        self.assertEqual(self.py.closest(probe)[0], self.rs.closest(probe)[0])
        self.assertAlmostEqual(self.py.centroid_score("anna", probe), self.rs.centroid_score("anna", probe), places=4)

    def test_merge_matches_python(self):
        old, new = person(5, 38, 0.3), person(5, 6, 0.3)
        native = face_engine.merge(old, new, 40)
        python = emb.merge(old, new, 40)
        self.assertEqual(native.shape, python.shape)
        self.assertTrue(np.allclose(np.sort(native @ python.T, axis=1)[:, -1], 1.0, atol=1e-4))

    def test_bad_rows_are_rejected(self):
        with self.assertRaises(ValueError):
            self.rs.book.replace([("x", b"\x00" * 7, None, False)])
        self.assertEqual(self.rs.verdict(np.zeros(5))["slug"], None)


def landmarks(yaw: float, depth: float) -> list:
    pts = [(-0.5, -0.4, 0.0), (0.5, -0.4, 0.0), (0.0, 0.1, depth), (-0.4, 0.5, 0.0), (0.4, 0.5, 0.0)]
    out = []
    for x, y, z in pts:
        xr, zr = x * np.cos(yaw) + z * np.sin(yaw), -x * np.sin(yaw) + z * np.cos(yaw)
        out += [300 + 220 * xr / (5 + zr), 240 + 220 * y / (5 + zr)]
    return out


def face_image(seed: int, mole: bool) -> np.ndarray:
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:112, 0:112]
    img = 110 + 40 * np.cos((x - 55.5) / 9) * np.cos(y / 13) + rng.uniform(-25, 25, (112, 112))
    if mole:
        img[52:62, 24:34] = 25
    return np.repeat(np.clip(img, 0, 255).astype(np.uint8)[:, :, None], 3, axis=2)


@unittest.skipIf(NATIVE is None, "modulo Rust nuxiva_native non installato")
class NativeSensesTest(unittest.TestCase):
    def test_turning_face_is_live_and_turning_photo_is_spoof(self):
        real, photo = face_engine.liveness(), face_engine.liveness()
        for i in range(16):
            yaw = float(np.sin(i * 0.5) * 0.4)
            a = real.update(landmarks(yaw, -0.4), i * 0.25, 0.55)
            b = photo.update(landmarks(yaw, 0.0), i * 0.25, 0.55)
        self.assertEqual((a["state"], b["state"]), ("live", "spoof"))
        self.assertGreater(a["depth"], b["depth"])

    def test_marks_tell_identical_twins_apart(self):
        rows = person(40, 16, 0.2)
        anna = [face_engine.marks_of(face_image(100 + i, False)) for i in range(6)]
        alba = [face_engine.marks_of(face_image(200 + i, True)) for i in range(6)]
        self.assertEqual(anna[0].shape, (face_engine.MARKS_DIM,))
        book = face_engine.NativeFaceBook(NATIVE, face_engine.Settings())
        book.replace([("anna", rows, None, False, np.array(anna)), ("alba", rows, None, False, np.array(alba))])
        probe = probes(rows, 7, 1, 0.05)[0]
        self.assertTrue(book.verdict(probe)["ambiguous"])
        verdict = book.verdict(probe, marks=face_engine.marks_of(face_image(300, True)))
        self.assertEqual((verdict["slug"], verdict["reason"]), ("alba", "segni particolari"))
        report = {r["slug"]: r for r in book.report()}
        self.assertEqual(report["alba"]["marks_samples"], 6)
        self.assertEqual([(m["region"], m["side"]) for m in report["alba"]["marks"]], [("cheek", "right")])
        self.assertEqual(report["anna"]["marks"], [])

    def test_look_traits_and_memory(self):
        found = face_engine.traits_of(face_image(9, False))
        self.assertEqual(set(found), {"glasses", "beard", "fringe", "cigarette"})
        self.assertTrue(all(0.0 <= v <= 1.0 for v in found.values()))
        self.assertIsNone(face_engine.traits_of(None))
        memory = __import__("nuxiva_native").RustFaceLook()
        events = []
        for i in range(20):
            events += memory.update({"samples": 8, "glasses": 0.9, "hair": "black"}, float(i))
        self.assertIn(("glasses", "on"), [(e["kind"], e["value"]) for e in events])
        self.assertTrue(memory.summary()["glasses"])
        with self.assertRaises(ValueError):
            __import__("nuxiva_native").RustFaceLook("{broken")

    def test_quality_and_light_reports(self):
        face = np.array([0, 0, 160, 160, *landmarks(0.0, -0.4)], dtype=np.float32)
        good = face_engine.quality(face_image(5, False), face, 640)
        self.assertGreater(good["score"], 60)
        self.assertEqual(good["kind"], "front")
        black = face_engine.light(np.zeros((48, 64, 3), np.uint8))
        self.assertEqual(black["issues"], ["black"])


if __name__ == "__main__":
    unittest.main()
