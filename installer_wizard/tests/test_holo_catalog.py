import asyncio
import base64
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agenti.hands.holo import hd
from agenti.hands.holo.catalog import fetch, finder, judge
from agenti.hands.holo.catalog.store import Catalog
from agenti.hands.holo.session import Session, session


def glb_chunks(blob: bytes) -> tuple[dict, bytes]:
    magic, version, total = blob[:4], *struct.unpack("<II", blob[4:12])
    json_len = struct.unpack("<I", blob[12:16])[0]
    doc = json.loads(blob[20:20 + json_len])
    bin_len = struct.unpack("<I", blob[20 + json_len:24 + json_len])[0]
    assert magic == b"glTF" and version == 2 and total == len(blob)
    return doc, blob[28 + json_len:28 + json_len + bin_len]


class FetchTest(unittest.TestCase):
    def test_only_trusted_https_hosts_are_allowed(self):
        self.assertTrue(fetch.allowed("https://api.polyhaven.com/assets?t=models"))
        self.assertTrue(fetch.allowed("https://dl.polyhaven.org/file/x.gltf"))
        for url in ("http://api.polyhaven.com/x", "https://user@api.polyhaven.com/x", "https://api.polyhaven.com:8443/x",
                    "https://evil.example/x", "https://api.polyhaven.com.evil.example/x", "file:///etc/passwd", "", None):
            self.assertFalse(fetch.allowed(url), url)

    def test_download_refuses_untrusted_host_before_network(self):
        with self.assertRaises(fetch.FetchError):
            asyncio.run(fetch.download("https://169.254.169.254/latest/meta-data"))

    def test_archive_paths_cannot_escape(self):
        for bad in ("../x.bin", "/etc/passwd", "a/../../x", "..", "a\x00b"):
            with self.assertRaises(fetch.FetchError):
                fetch.safe_name(bad)
        self.assertEqual(fetch.safe_name("textures\\skin.png"), "textures/skin.png")

    def test_gltf_with_external_buffer_and_image_becomes_single_glb(self):
        gltf = {"asset": {"version": "2.0"}, "buffers": [{"uri": "mesh.bin", "byteLength": 6}],
                "bufferViews": [{"buffer": 0, "byteOffset": 2, "byteLength": 4}],
                "images": [{"uri": "tex/skin%20a.png"}, {"uri": "data:image/png;base64," + base64.b64encode(b"PNG").decode()}]}
        files = {"model/scene.gltf": json.dumps(gltf).encode(), "model/mesh.bin": b"abcdef", "model/tex/skin a.png": b"IMG"}
        doc, binary = glb_chunks(fetch.pack_files(files))
        self.assertEqual(doc["buffers"], [{"byteLength": len(binary)}])
        self.assertEqual(doc["bufferViews"][0]["byteOffset"], 2)
        first = doc["bufferViews"][doc["images"][0]["bufferView"]]
        self.assertEqual(binary[first["byteOffset"]:first["byteOffset"] + first["byteLength"]], b"IMG")
        self.assertEqual(doc["images"][0]["mimeType"], "image/png")
        self.assertNotIn("uri", doc["images"][1])

    def test_missing_or_escaping_resource_is_rejected(self):
        gltf = {"buffers": [{"uri": "../../secret.bin"}]}
        with self.assertRaises(fetch.FetchError):
            fetch.pack_files({"m/scene.gltf": json.dumps(gltf).encode()})
        with self.assertRaises(fetch.FetchError):
            fetch.pack_files({"readme.txt": b"x"})

    def test_glb_passes_through(self):
        self.assertEqual(fetch.pack(b"glTF1234"), b"glTF1234")


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.catalog = Catalog(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_add_keeps_best_and_limits_entries(self):
        for score in (50, 90, 70, 60, 80):
            self.catalog.add("cuore", b"glTF", {"name": f"m{score}", "score": score})
        best = self.catalog.best("cuore")
        self.assertEqual(best["score"], 90)
        files = list(Path(self.tmp.name).glob("*.glb"))
        self.assertEqual(len(files), 4)
        self.assertEqual(oct(files[0].stat().st_mode & 0o777), "0o600")
        self.assertIsNone(self.catalog.best("polmone"))

    def test_path_rejects_traversal_and_unknown_ids(self):
        entry = self.catalog.add("dna", b"glTF", {"score": 1})
        self.assertIsNotNone(self.catalog.path(entry["id"]))
        for bad in ("../index", "index.json", entry["id"].upper(), "", None, "a" * 24):
            self.assertIsNone(self.catalog.path(bad))


class JudgeTest(unittest.TestCase):
    def test_final_score_weights_visual_and_penalises_background(self):
        report = {"score": 100}
        self.assertEqual(judge.final(report, {"match": 10, "quality": 10, "background": False}), 100)
        self.assertEqual(judge.final(report, {"match": 10, "quality": 10, "background": True}), 75)
        self.assertEqual(judge.final({"score": 0}, {"match": 0, "quality": 0, "background": True}), 0)

    def test_inspector_fails_closed_without_native_engine(self):
        with mock.patch("native_module.feature", return_value=None):
            with self.assertRaises(fetch.FetchError):
                judge.inspect(b"glTF")


class FinderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.catalog = Catalog(Path(self.tmp.name))
        self.patches = [mock.patch.object(finder, "catalog", self.catalog), mock.patch.object(finder, "key_of", side_effect=lambda s: s),
                        mock.patch.object(finder, "english", new=mock.AsyncMock(return_value="heart")),
                        mock.patch.object(finder.sketchfab, "token", return_value=""),
                        mock.patch.object(finder.state_store, "event")]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def candidate(self, uid, name):
        return {"source": "polyhaven", "uid": uid, "name": name, "license": "CC0", "author": "A", "page": "https://polyhaven.com/a/x",
                "thumbnail": "https://cdn.polyhaven.com/x.png", "faces": 20000, "animations": 0}

    def run_find(self, verdicts, scores):
        events = []
        cands = [self.candidate("a", "Cuore A"), self.candidate("b", "Cuore B")]
        report = lambda s: {"score": s, "animations": 0, "triangles": 50000, "reasons": []}
        with mock.patch.object(finder.polyhaven, "search", new=mock.AsyncMock(return_value=cands)), \
                mock.patch.object(finder.polyhaven, "download", new=mock.AsyncMock(return_value=b"glTF")), \
                mock.patch.object(judge, "look", new=mock.AsyncMock(side_effect=verdicts)), \
                mock.patch.object(judge, "inspect", side_effect=[report(s) for s in scores]):
            entry = asyncio.run(finder.find("cuore", lambda key, **p: events.append((key, p))))
        return entry, [k for k, _ in events]

    def test_rejects_low_score_then_picks_next_and_reports_each_step(self):
        good = {"match": 9, "quality": 9, "background": False}
        entry, keys = self.run_find([good, dict(good, quality=8)], [10, 90])
        self.assertEqual(entry["name"], "Cuore B")
        self.assertEqual(keys, ["searching", "rating", "downloading", "rejected", "downloading", "chosen"])
        self.assertEqual(self.catalog.best("cuore")["license"], "CC0")
        again = asyncio.run(finder.find("cuore"))
        self.assertEqual(again["id"], entry["id"])

    def test_wrong_subject_is_never_downloaded(self):
        wrong = {"match": 2, "quality": 10, "background": False}
        entry, keys = self.run_find([wrong, wrong], [])
        self.assertIsNone(entry)
        self.assertEqual(keys, ["searching", "rating", "none"])

    def test_disabled_catalog_does_no_search(self):
        with mock.patch.object(finder, "enabled", return_value=False), \
                mock.patch.object(finder.polyhaven, "search", new=mock.AsyncMock()) as search:
            self.assertIsNone(asyncio.run(finder.find("cuore")))
        search.assert_not_called()

    def test_asset_scene_points_to_display_endpoint(self):
        scene = finder.asset_scene({"id": "a" * 24, "name": "Cuore", "author": "A", "license": "CC0", "score": 88})
        self.assertEqual(scene["parts"], [])
        self.assertEqual(scene["asset"]["url"], f"/api/hands/display/holo/asset/{'a' * 24}")


class BuildTest(unittest.TestCase):
    def tearDown(self):
        session.close()

    def test_catalog_model_wins_over_generated_design(self):
        sid = session.begin("cuore", "realistic")
        entry = {"id": "b" * 24, "name": "Cuore", "author": "A", "license": "CC-BY", "score": 81}

        async def find(subject, notify, english=""):
            notify("chosen", name="Cuore", score=81)
            return entry

        with mock.patch.object(finder, "find", new=find), mock.patch.object(hd, "design", new=mock.AsyncMock()) as design, \
                mock.patch.object(finder, "cached", return_value=None), \
                mock.patch.object(finder, "english", new=mock.AsyncMock(return_value="heart")), \
                mock.patch("agenti.hands.holo.science.resolve.find", new=mock.AsyncMock(return_value=None)):
            asyncio.run(hd.build(sid, "cuore", None, "it"))
        design.assert_not_called()
        snap = session.snapshot()
        self.assertEqual(snap["source"], "catalog")
        self.assertEqual(snap["status"], "ready")
        self.assertEqual(snap["scene"]["asset"]["license"], "CC-BY")
        self.assertEqual(snap["progress"], {"key": "chosen", "params": {"name": "Cuore", "score": 81}})

    def test_progress_ignores_stale_session_and_clips_text(self):
        s = Session()
        sid = s.begin("dna")
        s.progress("old", "searching", source="x")
        self.assertEqual(s.snapshot()["progress"]["key"], "")
        s.progress(sid, "downloading", name="n" * 500)
        self.assertLess(len(s.snapshot()["progress"]["params"]["name"]), 200)


if __name__ == "__main__":
    unittest.main()
