import random
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from starlette.testclient import TestClient

import native_core
from agenti.nvr import archive as archive_mod
from agenti.nvr import notice as notice_mod
from agenti.nvr import policy_py, privacy, privacy_api, search_index, transcripts
from agenti.nvr import settings as nvr_settings
from agenti.nvr.api import admin_routes
from agenti.nvr.service import nvr
from agenti.nvr.store import EventStore
from agenti.nvr.vault import MediaVault

NATIVE = native_core.load()
READY = NATIVE is not None and hasattr(NATIVE, "nvr_audio_decision")
MASTER = bytes(range(32))
ROOMS = ["Bagno", "bagno ospiti", "Camera da letto", "CAMERETTA", "Soggiorno", "Cucina", "Salle de bains", "Chambre d'amis",
         "Baño principal", "Habitación", "Master Bedroom", "Living room", "Garage", "", "   ", "Studio", "Ingresso-WC",
         "Stanza da  letto", "letto", "salle", "x" * 300, "Dressing room", "Ufficio di Anna"]
EXTRAS = [[], ["studio"], ["ufficio anna"], ["x" * 65], ["garage", "living"], ["!!"]]


class PolicyTest(unittest.TestCase):
    def test_python_rules(self):
        self.assertEqual(policy_py.py_audio_decision("Bagno", True, True, []), (False, "private_room", True))
        self.assertEqual(policy_py.py_audio_decision("Cucina", True, False, []), (False, "notice_off", False))
        self.assertEqual(policy_py.py_audio_decision("Cucina", False, True, []), (False, "not_opted_in", False))
        self.assertEqual(policy_py.py_audio_decision("Cucina", True, True, []), (True, "allowed", False))
        self.assertTrue(policy_py.is_private_room("Ufficio di Anna", ["ufficio di anna"]))
        self.assertFalse(policy_py.is_private_room("Ufficio di Anna", ["ufficio anna"]))

    @unittest.skipUnless(READY, "nuxiva_native non installato")
    def test_parity(self):
        for room in ROOMS:
            for extra in EXTRAS:
                for opted in (True, False):
                    for notice in (True, False):
                        self.assertEqual(tuple(NATIVE.nvr_audio_decision(room, opted, notice, extra)),
                                         policy_py.py_audio_decision(room, opted, notice, extra), (room, extra))

    def test_overview(self):
        settings = {"audio_cameras": ["c1", "c2"], "notice_enabled": True, "private_rooms": []}
        out = privacy.overview([{"id": "c1", "name": "Cam 1", "room": "Cucina"}, {"id": "c2", "name": "Cam 2", "room": "Bagno"},
                                {"id": "c3", "name": "Cam 3", "room": "Soggiorno"}], settings)
        self.assertEqual(out["recording_audio"], ["c1"])
        self.assertEqual([c["reason"] for c in out["cameras"]], ["allowed", "private_room", "not_opted_in"])


class SettingsTest(unittest.TestCase):
    def test_privacy_validation(self):
        base = nvr_settings.load() | {"enabled": False}
        out = nvr_settings.validate({"audio_cameras": ["c1", "c1", "c-2"], "notice_enabled": 1, "notice_repeat_hours": 900,
                                     "private_rooms": ["  studio  ", "", "stanza   ospiti"]}, base)
        self.assertEqual(out["audio_cameras"], ["c-2", "c1"])
        self.assertTrue(out["notice_enabled"])
        self.assertEqual(out["notice_repeat_hours"], 168)
        self.assertEqual(out["private_rooms"], ["stanza ospiti", "studio"])
        self.assertFalse(nvr_settings.DEFAULTS["notice_enabled"])
        self.assertEqual(nvr_settings.DEFAULTS["audio_cameras"], [])
        for bad in ({"audio_cameras": ["../x"]}, {"audio_cameras": "c1"}, {"private_rooms": ["r"] * 51},
                    {"notice_repeat_hours": "x"}):
            with self.assertRaises(nvr_settings.SettingsError):
                nvr_settings.validate(bad, base)


class NoticeTest(unittest.TestCase):
    def setUp(self):
        self.now = [1000.0]
        self.quiet = [False]
        self.shown = []
        self.notice = notice_mod.RecordingNotice(show=lambda title, text, speak: self.shown.append((title, text, speak)),
                                                 quiet=lambda: self.quiet[0], clock=lambda: self.now[0])
        self.rows = [{"camera": "c1", "name": "Cam", "room": "Cucina", "allowed": True},
                     {"camera": "c2", "name": "Cam 2", "room": "Soggiorno", "allowed": True},
                     {"camera": "c3", "name": "Cam 3", "room": "Bagno", "allowed": False}]
        self.settings = {"notice_enabled": True, "notice_repeat_hours": 2}

    def test_cycle(self):
        with mock.patch.object(notice_mod, "language", return_value="it"):
            self.assertIsNone(self.notice.tick(self.rows, {"notice_enabled": False}))
            entry = self.notice.tick(self.rows, self.settings)
            self.assertEqual(entry["places"], ["Cucina", "Soggiorno"])
            self.assertIn("Cucina e Soggiorno", self.shown[-1][1])
            self.assertTrue(self.shown[-1][2])
            self.assertIsNone(self.notice.tick(self.rows, self.settings))
            self.now[0] += 7201
            self.assertIsNotNone(self.notice.tick(self.rows, self.settings))
            self.quiet[0] = True
            self.assertFalse(self.notice.tick(self.rows[:1], self.settings)["spoken"])
            self.assertTrue(self.notice.status()["pending"])
            self.quiet[0] = False
            self.assertTrue(self.notice.tick(self.rows[:1], self.settings)["spoken"])
            self.assertIsNone(self.notice.tick(self.rows[:1], self.settings))
            self.assertIsNotNone(self.notice.tick(self.rows[:1], self.settings, force=True))
            self.assertIsNone(self.notice.tick([], self.settings))
        self.assertEqual(notice_mod.message(self.rows, "en")[1].split(" the")[0], "In Cucina and Soggiorno")


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
                raw.write_bytes(random.Random(cam).randbytes(2000))
                self.archive.ingest(cam, raw)
        start = self.archive.catalog.get("cam1", "seg_20261112_100000")["start_ms"]
        for cam, rows in (("cam1", [("anna", "il pacco è arrivato"), ("marco", "grazie mille")]), ("cam2", [("marco", "chiavi in cucina")])):
            turns = [{"start_ms": start + i * 2000, "end_ms": start + i * 2000 + 1500, "text": text, "speaker": who,
                      "speaker_score": 0.8, "voice": None} for i, (who, text) in enumerate(rows)]
            self.tx.save(cam, "seg_20261112_100000", {"camera": cam, "segment": "seg_20261112_100000", "start_ms": start, "turns": turns})
            self.index.index_transcript(cam, "seg_20261112_100000", turns)

    def tearDown(self):
        self.tmp.cleanup()


class PersonTest(Base):
    def test_export_and_erase(self):
        data = privacy.export_person("marco", self.tx)
        self.assertEqual([t["text"] for t in data["turns"]], ["chiavi in cucina", "grazie mille"])
        self.assertEqual(data["segments"], ["cam1/seg_20261112_100000", "cam2/seg_20261112_100000"])
        with self.assertRaises(ValueError):
            privacy.export_person("../x", self.tx)
        out = privacy.erase_person("marco", self.tx, self.index)
        self.assertEqual((out["turns_removed"], out["segments_touched"], out["segments_deleted"]), (2, 2, 0))
        self.assertEqual(privacy.export_person("marco", self.tx)["turns"], [])
        self.assertEqual(self.index.search("grazie", None, 0, 10**13), [])
        self.assertEqual(len(self.index.search("pacco", None, 0, 10**13)), 1)
        self.assertIsNotNone(self.archive.catalog.get("cam2", "seg_20261112_100000"))

    def test_erase_with_clips(self):
        out = privacy.erase_person("anna", self.tx, self.index, self.archive, delete_segments=True)
        self.assertEqual(out["segments_deleted"], 1)
        self.assertIsNone(self.archive.catalog.get("cam1", "seg_20261112_100000"))
        self.assertFalse(self.tx.exists("cam1", "seg_20261112_100000"))
        self.assertEqual(self.index.search("grazie", None, 0, 10**13), [])
        self.assertEqual(len(self.index.search("chiavi", None, 0, 10**13)), 1)


class ApiTest(Base):
    def setUp(self):
        super().setUp()
        self.saved = dict(nvr.settings)
        self.store = EventStore(Path(self.tmp.name) / "events.db")
        nvr._store = self.store
        self.shown = []
        fresh = notice_mod.RecordingNotice(show=lambda title, text, speak: self.shown.append(text), quiet=lambda: False)
        self.patches = [mock.patch.object(nvr_settings, "save", lambda settings: None),
                        mock.patch.object(privacy_api, "notice", fresh),
                        mock.patch.object(privacy_api, "camera_names", lambda: {"cam1": {"name": "Ingresso", "room": "Cucina"},
                                                                                 "cam2": {"name": "Bagno", "room": "Bagno"}}),
                        mock.patch.object(privacy_api, "_deps", lambda: (self.archive, self.index)),
                        mock.patch.object(privacy_api, "_audit", lambda *a: None),
                        mock.patch.object(notice_mod, "language", return_value="it")]
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
        nvr.settings = self.saved
        self.store.close()
        super().tearDown()

    def test_policy_notice_and_person(self):
        state = self.client.get("/api/nvr/privacy").json()
        self.assertEqual([c["reason"] for c in state["cameras"]], ["notice_off", "private_room"])
        self.assertEqual(self.client.post("/api/nvr/notice/announce").status_code, 409)
        state = self.client.put("/api/nvr/privacy", json={"audio_cameras": ["cam1", "cam2"], "notice_enabled": True,
                                                          "enabled": True, "mqtt_host": "evil"}).json()
        self.assertEqual(state["recording_audio"], ["cam1"])
        self.assertFalse(nvr.settings["enabled"] and nvr.settings["mqtt_host"] == "evil")
        self.assertEqual(self.client.put("/api/nvr/privacy", json={"audio_cameras": ["../x"]}).status_code, 400)
        self.assertEqual(self.client.post("/api/nvr/notice/announce").json()["places"], ["Cucina"])
        self.assertIn("Cucina", self.shown[-1])
        res = self.client.get("/api/nvr/privacy/person/anna")
        self.assertEqual(res.headers["cache-control"], "no-store")
        self.assertEqual(len(res.json()["turns"]), 1)
        self.assertEqual(self.client.get("/api/nvr/privacy/person/Bad%20Slug").status_code, 400)
        out = self.client.post("/api/nvr/privacy/person/anna/erase", json={"delete_segments": False}).json()
        self.assertEqual(out["turns_removed"], 1)


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg non installato")
class StripAudioTest(unittest.TestCase):
    def test_strip(self):
        from agenti.cameras.recorder import strip_audio
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "seg.mp4"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=64x64:rate=5", "-f", "lavfi",
                            "-i", "sine=frequency=440", "-t", "1", "-c:v", "mpeg4", "-c:a", "aac", "-shortest", str(path)], check=True)
            strip_audio(path)
            probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path)],
                                   capture_output=True, text=True, check=True)
            self.assertEqual(probe.stdout.split(), ["video"])


if __name__ == "__main__":
    unittest.main()
