import json
import os
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

import access
import nuxiva_supervisor
import system_api
from features.desktop.screens import Screens, role_of
from features.stage import api as stage_api
from features.stage import director, native, particles
from features.stage.service import Stage, clean_context
from features.stage.store import ParticleStore, concept_key

HEADERS = {"X-Nuxiva-Request": "1"}
SPEC = {"parts": [{"shape": "box", "size": [1.2, 0.3, 0.6], "color": "#ff5533"},
                  {"shape": "cylinder", "size": [0.3, 0.1, 0.3], "at": [-0.8, -0.35, 0.6], "rot": [90, 0, 0]},
                  {"shape": "torus", "size": [0.5, 0.5, 0.5], "at": [0, 0.8, 0], "weight": 0.5},
                  {"shape": "helix", "size": [0.2, 0.6, 0.2], "at": [1, 0, 0], "rot": [0, 30, 15]},
                  {"shape": "sphere"}, {"shape": "cone"}, {"shape": "plane", "size": [2, 1, 2], "at": [0, -1, 0]}]}


def request(now, surfaces, previous=None, **ctx):
    return {"now_ms": now, "context": clean_context(ctx), "surfaces": surfaces, "previous": previous or {}, "weights": {}}


def plan_with(now, ctx, settings=None, prev=None):
    stage = Stage()
    stage.weights = {}
    surfaces = stage.surfaces(clean_context(ctx), settings or {}, set())
    return director.plan_python({"now_ms": now, "context": clean_context(ctx), "surfaces": surfaces,
                                 "previous": prev or {}, "weights": {}})


class DirectorTest(unittest.TestCase):
    def test_chat_yields_to_the_voice_and_comes_back_when_typing(self):
        voice = plan_with(10_000, {"listening": True, "people": 1})
        self.assertEqual(voice["context_key"], "voice")
        self.assertEqual(voice["surfaces"]["chat"]["state"], "min")
        typing = plan_with(10_000, {"typing": True, "listening": True, "people": 1})
        self.assertEqual(typing["surfaces"]["chat"]["state"], "shown")
        self.assertEqual(typing["surfaces"]["mic"]["state"], "shown")

    def test_one_listening_meter_only(self):
        out = plan_with(0, {"people": 1}, {"surfaces": {"rail_voice": True}})
        self.assertEqual(out["surfaces"]["mic"]["state"], "shown")
        self.assertEqual(out["surfaces"]["rail_voice"]["state"], "hidden")

    def test_other_modes_hide_ambient_surfaces(self):
        out = plan_with(0, {"mode": "brain", "people": 2})
        for sid in ("rail_home", "rail_scan", "thinking", "brain_badge", "project"):
            self.assertEqual(out["surfaces"][sid]["state"], "hidden", sid)

    def test_desk_widget_replaces_its_duplicate(self):
        out = plan_with(0, {"project": True, "desk": ["project_status"], "people": 1})
        self.assertEqual(out["surfaces"]["project"]["state"], "hidden")
        self.assertEqual(out["surfaces"]["w:project_status"]["state"], "shown")

    def test_disabled_surface_stays_hidden(self):
        out = plan_with(0, {"people": 1}, {"show_presence": False})
        self.assertEqual(out["surfaces"]["presence"]["state"], "hidden")

    def test_dwell_keeps_a_fresh_state(self):
        first = plan_with(1_000, {"people": 1})
        prev = {k: {"state": v["state"], "since_ms": v["since_ms"]} for k, v in first["surfaces"].items()}
        quick = plan_with(1_500, {"listening": True, "people": 1}, prev=prev)
        self.assertEqual(quick["surfaces"]["chat"]["state"], "shown")
        later = plan_with(5_000, {"listening": True, "people": 1}, prev=prev)
        self.assertEqual(later["surfaces"]["chat"]["state"], "min")

    def test_feedback_moves_the_weight_and_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch("features.stage.service.WEIGHTS_FILE", Path(tmp) / "w.json"):
            stage = Stage()
            stage.plan("kiosk", {"listening": True, "people": 1}, {})
            for _ in range(40):
                weight = stage.feedback("kiosk", "chat", True)
            self.assertLessEqual(weight, director.WEIGHT_LIMIT)
            self.assertGreater(weight, 30)
            self.assertEqual(os.stat(Path(tmp) / "w.json").st_mode & 0o777, 0o600)
            with self.assertRaises(ValueError):
                stage.feedback("kiosk", "../../etc", True)
            with self.assertRaises(KeyError):
                stage.feedback("nobody", "chat", True)

    def test_context_is_sanitised(self):
        ctx = clean_context({"mode": "<script>", "people": "999", "typing": "yes", "desk": ["ok_id", "BAD ID", 3] * 30})
        self.assertEqual(ctx["mode"], "face")
        self.assertEqual(ctx["people"], 64)
        self.assertIs(ctx["typing"], False)
        self.assertEqual(ctx["desk"], ["ok_id"])

    @unittest.skipIf(native.lib is None, "nuxiva_native not built")
    def test_rust_and_python_agree(self):
        stage = Stage()
        cases = [{"people": 1}, {"listening": True, "people": 2}, {"typing": True}, {"mode": "flow"},
                 {"project": True, "desk": ["project_status", "music"], "music": True, "people": 1}, {}]
        for i, ctx in enumerate(cases):
            clean = clean_context(ctx)
            req = {"now_ms": 50_000 + i, "context": clean, "surfaces": stage.surfaces(clean, {}, {"music"}),
                   "previous": {"chat": {"state": "min", "since_ms": 1}}, "weights": {"chat": {"voice": 12.5}}}
            rust = json.loads(native.lib.stage_plan(json.dumps(req)))
            self.assertEqual(rust, director.plan_python(req), ctx)


class ParticlesTest(unittest.TestCase):
    def test_sample_is_deterministic_and_well_formed(self):
        blob = particles.sample_python(SPEC, 3000, 7)
        self.assertEqual(blob, particles.sample_python(SPEC, 3000, 7))
        self.assertNotEqual(blob, particles.sample_python(SPEC, 3000, 8))
        self.assertEqual(particles.count(blob), 3000)
        coords = struct.unpack("<9000h", blob[12:12 + 18000])
        self.assertEqual(max(abs(v) for v in coords), 32767)

    def test_bad_specs_are_rejected(self):
        for bad in (None, {}, {"parts": []}, {"parts": [{"shape": "pyramid"}]},
                    {"parts": [{"shape": "box", "size": [1, 1]}]}, {"parts": [{"shape": "box", "color": "red"}]},
                    {"parts": [{"shape": "box", "at": [float("nan"), 0, 0]}]}, {"parts": [{"shape": "box", "weight": True}]},
                    {"parts": [{"shape": "box"}] * 25}):
            with self.assertRaises(particles.ParticleError, msg=bad):
                particles.validate(bad)
        with self.assertRaises(particles.ParticleError):
            particles.sample_python(SPEC, 100, 1)

    def test_decoder_is_strict(self):
        blob = particles.sample_python(SPEC, 256, 1)
        for bad in (blob[:-1], b"XXXX" + blob[4:], blob[:4] + b"\x02" + blob[5:], blob[:5] + b"\x04" + blob[6:],
                    blob[:8] + struct.pack("<I", 70_000) + blob[12:], b""):
            with self.assertRaises(particles.ParticleError):
                particles.count(bad)

    @unittest.skipIf(native.lib is None, "nuxiva_native not built")
    def test_rust_and_python_produce_the_same_bytes(self):
        clean = particles.validate(SPEC)
        for count, seed in ((256, 1), (5000, 42), (12_000, 2 ** 63 + 5)):
            rust = bytes(native.lib.particles_sample(json.dumps(clean), count, seed))
            self.assertEqual(rust, particles.sample_python(clean, count, seed), (count, seed))
            self.assertEqual(native.lib.particles_count(rust), count)


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.store = ParticleStore(self.root)

    def test_concepts_are_normalised(self):
        self.assertEqual(concept_key("  Motore   Diesel! "), "motore diesel")
        self.assertEqual(concept_key("Città/../../etc"), "citta etc")

    def test_round_trip_with_private_files(self):
        blob = particles.sample_python(SPEC, 512, 3)
        entry = self.store.put("Bicicletta", SPEC, blob)
        self.assertEqual(self.store.blob(entry["digest"]), blob)
        self.assertEqual(ParticleStore(self.root).lookup("bicicletta")["digest"], entry["digest"])
        for path in (self.root / ".key", self.root / "index.json", self.root / "blobs" / f"{entry['digest']}.nxpc"):
            self.assertEqual(os.stat(path).st_mode & 0o077, 0, path)

    def test_tampered_index_is_discarded(self):
        entry = self.store.put("ruota", SPEC, particles.sample_python(SPEC, 256, 3))
        doc = json.loads((self.root / "index.json").read_text())
        doc["concepts"]["ruota"]["digest"] = "0" * 64
        (self.root / "index.json").write_text(json.dumps(doc))
        self.assertIsNone(ParticleStore(self.root).lookup("ruota"))
        self.assertIsNotNone(entry)

    def test_corrupted_blob_is_refused(self):
        entry = self.store.put("vite", SPEC, particles.sample_python(SPEC, 256, 3))
        path = self.root / "blobs" / f"{entry['digest']}.nxpc"
        data = bytearray(path.read_bytes())
        data[20] ^= 0xFF
        path.write_bytes(bytes(data))
        self.assertIsNone(ParticleStore(self.root).blob(entry["digest"]))
        self.assertIsNone(self.store.blob("../" + entry["digest"]))


class StageApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(nuxiva_supervisor.public)

    def setUp(self):
        self.local = False
        self.store = ParticleStore(Path(tempfile.mkdtemp()))
        for patch in (mock.patch.object(access, "is_local", lambda request: self.local),
                      mock.patch.object(stage_api, "store", self.store),
                      mock.patch.object(stage_api, "stage", Stage())):
            patch.start()
            self.addCleanup(patch.stop)

    def test_network_clients_are_refused(self):
        self.assertEqual(self.client.post("/api/stage/plan", json={"client": "kiosk"}, headers=HEADERS).status_code, 401)
        self.assertEqual(self.client.get("/api/particles/blob/" + "a" * 64).status_code, 401)

    def test_plan_validates_input(self):
        self.local = True
        self.assertEqual(self.client.post("/api/stage/plan", json={"client": "../x"}, headers=HEADERS).status_code, 400)
        big = self.client.post("/api/stage/plan", content=b"{" + b" " * 20_000 + b"}", headers={**HEADERS, "Content-Type": "application/json"})
        self.assertEqual(big.status_code, 413)
        r = self.client.post("/api/stage/plan", json={"client": "kiosk", "context": {"typing": True}}, headers=HEADERS)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["surfaces"]["chat"]["state"], "shown")
        fb = self.client.post("/api/stage/feedback", json={"client": "kiosk", "surface": "chat", "wanted": "yes"}, headers=HEADERS)
        self.assertEqual(fb.status_code, 400)

    def test_blob_is_served_with_strict_headers(self):
        self.local = True
        entry = self.store.put("scatola", SPEC, particles.sample_python(SPEC, 256, 1))
        r = self.client.get(f"/api/particles/blob/{entry['digest']}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["x-content-type-options"], "nosniff")
        self.assertIn("default-src 'none'", r.headers["content-security-policy"])
        self.assertEqual(particles.count(r.content), 256)
        self.assertEqual(self.client.get("/api/particles/blob/" + "f" * 64).status_code, 404)
        self.assertEqual(self.client.get("/api/particles/blob/NOTHEX").status_code, 400)


class ScreenRolesTest(unittest.TestCase):
    def screens(self, *numbers):
        s = Screens()
        for i, n in enumerate(numbers):
            s.hello(n, i * 1920, 1920, 1080, local=True)
        return s

    def test_roles_follow_the_number_of_screens(self):
        with mock.patch("features.desktop.screens.configured_roles", lambda: {}):
            self.assertEqual(self.screens(0).roles(), {0: "agent"})
            self.assertEqual(self.screens(0, 1).roles(), {0: "agent", 1: "work"})
            self.assertEqual(self.screens(0, 1, 2).roles(), {0: "agent", 1: "work", 2: "visual"})
            self.assertEqual(self.screens(0, 1).screen_for_role("visual"), 1)
            self.assertEqual(self.screens(0).screen_for_role("visual"), 0)

    def test_work_goes_to_the_workbench_screen(self):
        with mock.patch("features.desktop.screens.configured_roles", lambda: {}):
            s = self.screens(0, 1, 2)
            items = s.assign([{"id": "repair_workbench"}, {"id": "diorama"}, {"id": "weather"}, {"id": "alarm", "urgent": True}], {})
            self.assertEqual([i["screen"] for i in items], [1, 2, 0, -1])
            alone = self.screens(0).assign([{"id": "repair_workbench"}, {"id": "weather"}], {})
            self.assertEqual([i["screen"] for i in alone], [-1, -1])

    def test_role_hint_from_the_widget(self):
        self.assertEqual(role_of({"id": "weather", "screen_role": "visual"}), "visual")
        self.assertEqual(role_of({"id": "code_view", "screen_role": "nonsense"}), "work")

    def test_screen_roles_setting_is_validated(self):
        self.assertEqual(system_api._screen_roles({"0": "agent", "1": "visual", "17": "work", "2": "root", "x": "work", 3: "work",
                                                   "٣": "work"}), {"0": "agent", "1": "visual"})
        self.assertEqual(system_api._screen_roles("bad"), {})


if __name__ == "__main__":
    unittest.main()
