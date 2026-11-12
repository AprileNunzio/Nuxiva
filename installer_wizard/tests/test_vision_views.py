import json
import unittest

import cv2
import numpy as np
from fastapi import HTTPException

from tests.test_vision_service import face_row, service, vectors

import views as vviews
from features.people import views as pviews


def textured(size=200) -> np.ndarray:
    rng = np.random.default_rng(1)
    y, x = np.mgrid[0:size, 0:size]
    base = 120 + 50 * np.sin(x / 7.0) * np.cos(y / 11.0) + rng.normal(0, 18, (size, size))
    return np.repeat(np.clip(base, 0, 255).astype(np.uint8)[:, :, None], 3, axis=2)


def jpeg(h=120, w=100) -> bytes:
    ok, data = cv2.imencode(".jpg", np.full((h, w, 3), 128, dtype=np.uint8))
    return data.tobytes()


class PoseTest(unittest.TestCase):
    def test_front_three_quarter_and_profile(self):
        self.assertEqual(vviews.pose_of(np.array(face_row(0, 0, 100, 100), dtype=np.float32)), "front")
        turned = face_row(0, 0, 100, 100)
        turned[8] = 50 + 0.3 * 40
        self.assertEqual(vviews.pose_of(np.array(turned, dtype=np.float32)), "three_left")
        turned[8] = 50 - 0.8 * 40
        self.assertEqual(vviews.pose_of(np.array(turned, dtype=np.float32)), "right")

    def test_decode_rejects_garbage_and_oversize(self):
        with self.assertRaises(ValueError):
            vviews.decode(b"not an image")
        with self.assertRaises(ValueError):
            vviews.decode(b"")
        self.assertEqual(vviews.decode(jpeg()).shape[:2], (120, 100))


class ViewsServiceTest(unittest.TestCase):
    def setUp(self):
        self.gallery, self.views = service.gallery, service.views
        for slug in list(self.gallery.people):
            self.gallery.delete(slug)
        self.recognizer = self.views.recognizer
        self.detector = self.views.detector
        self.detector.faces = []

    def test_profile_photo_adds_samples_and_is_recorded(self):
        rgb = vectors(7)
        self.gallery.save("Anna", list(rgb[:6]), np.zeros((20, 20, 3), np.uint8), slug="anna")
        self.recognizer.vec = rgb[8].astype(np.float32)
        self.detector.faces = [face_row(20, 20, 160, 160)]
        r = self.views.add("anna", "Anna", "left", textured())
        self.assertEqual((r["kind"], r["face"], r["duplicate"]), ("left", True, False))
        self.assertGreater(r["samples"], 6)
        self.assertGreater(r["quality"]["score"], 30)
        self.assertEqual(r["views"]["left"], 1)
        self.assertTrue((vviews.FACES / "anna" / "photos" / r["photo"]).is_file())

    def test_setup_analysis_reports_real_pose_quality_and_light(self):
        self.detector.faces = [face_row(20, 20, 160, 160)]
        report = self.views.analyze(textured())
        self.assertTrue(report["face"])
        self.assertEqual(report["frame"], [200, 200])
        self.assertEqual(report["quality"]["kind"], "front")
        self.assertGreater(report["quality"]["score"], 30)
        self.assertGreater(report["distance_cm"], 0)
        self.assertEqual(len(report["points"]), 10)
        self.assertTrue(all(0.0 <= v <= 1.0 for v in report["box"] + report["points"]))
        json.dumps(report)
        self.detector.faces = []
        black = self.views.analyze(np.zeros((120, 160, 3), np.uint8))
        self.assertFalse(black["face"])
        self.assertIn("black", black["light"]["issues"])

    def test_the_same_photo_twice_adds_no_duplicate_sample(self):
        rgb = vectors(8)
        self.gallery.save("Anna", list(rgb[:6]), np.zeros((20, 20, 3), np.uint8), slug="anna")
        self.recognizer.vec = rgb[2].astype(np.float32)
        self.detector.faces = [face_row(20, 20, 160, 160)]
        r = self.views.add("anna", "Anna", "front", textured())
        self.assertTrue(r["duplicate"])
        self.assertEqual(r["samples"], 6)

    def test_a_dark_blurry_photo_is_refused_with_the_reasons(self):
        self.gallery.save("Anna", list(vectors(9)[:6]), np.zeros((20, 20, 3), np.uint8), slug="anna")
        self.recognizer.vec = vectors(9)[7].astype(np.float32)
        self.detector.faces = [face_row(10, 10, 40, 40)]
        with self.assertRaises(ValueError) as caught:
            self.views.add("anna", "Anna", "front", np.full((100, 100, 3), 6, np.uint8))
        self.assertIn("scura", str(caught.exception))

    def test_body_photo_without_face_is_kept(self):
        self.gallery.save("Bea", list(vectors(9)[:6]), np.zeros((20, 20, 3), np.uint8), slug="bea")
        r = self.views.add("bea", "Bea", "body", np.zeros((300, 120, 3), np.uint8))
        self.assertEqual((r["kind"], r["face"]), ("body", False))

    def test_face_kind_without_face_is_refused(self):
        self.gallery.save("Ciro", list(vectors(11)[:6]), np.zeros((20, 20, 3), np.uint8), slug="ciro")
        with self.assertRaises(ValueError):
            self.views.add("ciro", "Ciro", "front", np.zeros((100, 100, 3), np.uint8))

    def test_someone_else_face_is_refused(self):
        anna, dario = vectors(21), vectors(55)
        self.gallery.save("Anna", list(anna), np.zeros((20, 20, 3), np.uint8), slug="anna")
        self.gallery.save("Dario", list(dario), np.zeros((20, 20, 3), np.uint8), slug="dario")
        self.recognizer.vec = dario[0].astype(np.float32)
        self.detector.faces = [face_row(10, 10, 60, 60)]
        with self.assertRaises(ValueError):
            self.views.add("anna", "Anna", "front", np.zeros((100, 100, 3), np.uint8))
        meta = json.loads((vviews.FACES / "anna" / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["samples"], len(anna))


class SupervisorViewsTest(unittest.TestCase):
    def test_kind_of_and_photo_id_validation(self):
        self.assertEqual(pviews.kind_of("three_left_1728000000123"), "three_left")
        self.assertEqual(pviews.kind_of("photo_1728000000"), "sample")
        pviews.check_photo_id("body_1728000000123.jpg")
        pviews.check_photo_id("photo_primary")
        for bad in ("../meta.json", "..jpg", "a/b.jpg", "x.png", ".hidden.jpg"):
            with self.assertRaises(HTTPException):
                pviews.check_photo_id(bad)


if __name__ == "__main__":
    unittest.main()


class AutoViewTest(unittest.TestCase):
    def setUp(self):
        self.gallery, self.views = service.gallery, service.views
        for slug in list(self.gallery.people):
            self.gallery.delete(slug)
        self.gallery.save("Ciro", list(vectors(5)[:6]), np.zeros((20, 20, 3), np.uint8), slug="ciro")
        rng = np.random.default_rng(3)
        self.frame = rng.integers(0, 255, (300, 300, 3), dtype=np.uint8)

    def test_pose_is_filed_automatically_up_to_the_cap(self):
        face = np.array(face_row(80, 80, 120, 120), dtype=np.float32)
        for _ in range(vviews.AUTO_VIEW_CAP + 2):
            self.views.auto("ciro", self.frame, face)
        meta = json.loads((vviews.FACES / "ciro" / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["views"]["front"], vviews.AUTO_VIEW_CAP)

    def test_small_or_blurry_faces_are_skipped(self):
        small = np.array(face_row(80, 80, 30, 30), dtype=np.float32)
        self.assertIsNone(self.views.auto("ciro", self.frame, small))
        flat = np.full((300, 300, 3), 90, dtype=np.uint8)
        big = np.array(face_row(80, 80, 120, 120), dtype=np.float32)
        self.assertIsNone(self.views.auto("ciro", flat, big))
