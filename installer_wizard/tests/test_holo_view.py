import asyncio
import json
import unittest
from unittest import mock

import math

from agenti.hands.holo import commands, exact, fallback, hd
from agenti.hands.holo.session import Session, session


def cell() -> dict:
    return {"parts": [
        {"name": "membrana", "shape": "sphere", "radius": 10, "position": [0, 0, 0]},
        {"name": "nucleo", "shape": "sphere", "radius": 3, "position": [0, 0, 0], "motion": "pulse"},
        {"name": "mitocondrio", "shape": "capsule", "radius": 1, "height": 3, "position": [5, 0, 0]},
    ]}


class PrepareTest(unittest.TestCase):
    def test_model_scene_is_unit_sized_layered_and_animated(self):
        scene = fallback.prepare(cell())
        self.assertEqual(scene["euler"], "XYZ")
        self.assertEqual(scene["layers"], 2)
        self.assertEqual([p["layer"] for p in scene["parts"]], [0, 1, 1])
        self.assertEqual(scene["parts"][1]["motion"], "pulse")
        self.assertEqual(scene["parts"][1]["explode"], [0.0, 0.0, 0.0])
        self.assertGreater(scene["parts"][2]["explode"][0], 0.3)
        for part in scene["parts"]:
            for axis in range(3):
                self.assertGreaterEqual(part["at"][axis] - part["half"][axis], -1.001)
                self.assertLessEqual(part["at"][axis] + part["half"][axis], 1.001)

    def test_particle_spec_maps_all_primitives(self):
        shapes = ["sphere", "box", "cylinder", "cone", "torus", "helix", "plane", "cloud", "disc", "spiral", "ring", "halo", "orbit"]
        spec = {"source": "particles", "parts": [{"shape": s, "size": [0.5, 0.8, 0.5], "at": [0.1, 0.2, 0], "rot": [0, 45, 0]} for s in shapes]}
        scene = fallback.prepare(spec)
        self.assertEqual(scene["euler"], "ZYX")
        self.assertEqual(len(scene["parts"]), len(shapes))
        self.assertTrue(scene["parts"][7]["soft"])
        self.assertEqual(scene["parts"][10]["shape"], "torus")

    def test_hostile_values_are_sanitized(self):
        scene = fallback.prepare({"title": "<script>x</script>", "parts": [
            {"name": "a\x07<img onerror=1>", "shape": "box", "size": [1e30, -5, "x"], "position": [float("inf"), 0, 0],
             "color": "red", "motion": "explode()", "layer": 99},
            {"shape": "unknown"}, "nope"]})
        self.assertNotIn("<", scene["title"])
        part = scene["parts"][0]
        self.assertNotIn("<", part["name"])
        self.assertTrue(part["color"].startswith("#"))
        self.assertEqual(part["motion"], "none")
        self.assertEqual(part["layer"], 7)
        with self.assertRaises(ValueError):
            fallback.prepare({"parts": []})

    def test_native_and_fallback_agree_when_native_is_built(self):
        try:
            import nuxiva_native
        except ImportError:
            self.skipTest("motore nativo non compilato")
        if not hasattr(nuxiva_native, "holo_prepare"):
            self.skipTest("motore nativo senza holo_prepare")
        native = json.loads(nuxiva_native.holo_prepare(json.dumps(cell())))
        python = fallback.prepare(cell())
        self.assertEqual([p["layer"] for p in native["parts"]], [p["layer"] for p in python["parts"]])
        for a, b in zip(native["parts"], python["parts"]):
            for x, y in zip(a["at"] + a["half"], b["at"] + b["half"]):
                self.assertAlmostEqual(x, y, places=4)


class SessionTest(unittest.TestCase):
    def test_designed_scene_is_not_downgraded_by_late_draft(self):
        s = Session(clock=lambda: 100.0)
        sid = s.begin("cuore", "realistic")
        self.assertTrue(s.scene_ready(sid, {"parts": [1]}, "designed"))
        self.assertFalse(s.scene_ready(sid, {"parts": [2]}, "draft"))
        self.assertFalse(s.scene_ready("other", {"parts": [3]}, "designed"))
        snap = s.snapshot()
        self.assertEqual(snap["status"], "ready")
        self.assertEqual(snap["scene"], {"parts": [1]})
        self.assertIsNone(s.brief()["scene"])

    def test_expiry_hides_scene_and_commands_are_validated(self):
        now = [0.0]
        s = Session(clock=lambda: now[0])
        s.begin("dna")
        s.command("zoom_in")
        self.assertEqual(s.snapshot()["command"], {"seq": 1, "name": "zoom_in"})
        with self.assertRaises(ValueError):
            s.command("rm -rf")
        with self.assertRaises(ValueError):
            s.set_mode("wireframe")
        now[0] = 10_000.0
        self.assertFalse(s.active())
        self.assertIsNone(s.snapshot()["scene"])

    def test_failure_keeps_draft(self):
        s = Session()
        sid = s.begin("motore")
        s.scene_ready(sid, {"parts": [1]}, "draft")
        s.failed(sid, "BrainUnavailable")
        self.assertEqual(s.snapshot()["status"], "draft_only")


class CommandsTest(unittest.TestCase):
    def tearDown(self):
        session.close()

    def test_initial_mode_reads_the_request(self):
        self.assertEqual(commands.initial_mode("fammi vedere come è fatto un cuore in 3D", "it"), "realistic")
        self.assertEqual(commands.initial_mode("fammi vedere l'anatomia del cuore", "it"), "anatomy")
        self.assertEqual(commands.initial_mode("fammi vedere come è fatto il DNA", "it"), "particles")
        self.assertEqual(commands.initial_mode("show me a heart in 3D", "en"), "realistic")
        self.assertEqual(commands.initial_mode("muéstrame la anatomía del corazón", "es"), "anatomy")

    def test_commands_only_while_a_view_is_active(self):
        self.assertIsNone(asyncio.run(commands.answer("ingrandisci", "it")))
        session.begin("dna")
        out = asyncio.run(commands.answer("ingrandisci", "it"))
        self.assertEqual(out["intent"], "holo")
        self.assertEqual(session.snapshot()["command"]["name"], "zoom_in")
        out = asyncio.run(commands.answer("passa alla modalità anatomia", "it"))
        self.assertEqual(session.snapshot()["mode"], "anatomy")
        self.assertIn("dna", out["reply"])
        self.assertIsNone(asyncio.run(commands.answer("fammi vedere come è fatto un motore", "it")))
        long_text = "ruota " + "parola " * 20
        self.assertIsNone(asyncio.run(commands.answer(long_text, "it")))

    def test_follow_starts_session_and_background_build(self):
        visual = {"reply": "x", "ui": {"mode": "face", "particles": {"concept": "cuore"}}}
        spec = {"parts": [{"shape": "sphere", "size": [1, 1, 1], "at": [0, 0, 0]}]}
        with mock.patch("agenti.particles.store.store.lookup", return_value={"spec": spec}), \
                mock.patch.object(commands, "background") as bg:
            out = commands.follow(visual, "fammi vedere come è fatto un cuore in 3d", "it")
            bg.call_args.args[0].close()
        self.assertEqual(out["ui"]["holo"]["mode"], "realistic")
        self.assertEqual(out["ui"]["holo"]["subject"], "cuore")
        self.assertTrue(session.active())

    def test_build_uses_draft_then_reports_failure(self):
        sid = session.begin("cuore", "realistic")
        spec = {"parts": [{"shape": "sphere", "size": [1, 1, 1], "at": [0, 0, 0]}]}
        with mock.patch.object(hd, "design", side_effect=RuntimeError("offline")):
            asyncio.run(hd.build(sid, "cuore", spec, "it"))
        snap = session.snapshot()
        self.assertEqual(snap["status"], "draft_only")
        self.assertEqual(snap["source"], "draft")
        self.assertEqual(len(snap["scene"]["parts"]), 1)


class ExactTest(unittest.TestCase):
    def tearDown(self):
        session.close()

    def test_dna_is_recognised_in_every_language(self):
        for text in ("dna", "il DNA", "l'acido desossiribonucleico", "la doppia elica", "ADN", "double helix"):
            self.assertEqual(exact.kind_of(text), "dna", text)
        self.assertIsNone(exact.kind_of("cuore"))

    def test_dna_scene_is_b_form_with_localized_labels(self):
        scene = exact.scene("dna", "it")
        names = [p["name"] for p in scene["parts"]]
        self.assertEqual(names.count("dna_phosphate"), 40)
        self.assertEqual(names.count("dna_backbone"), 38)
        labels = {p["label"] for p in scene["parts"]}
        self.assertIn("Adenina (A)", labels)
        self.assertIn("Scheletro zucchero-fosfato", labels)
        self.assertEqual(scene["title"], "DNA · doppia elica B")
        self.assertEqual(exact.scene("dna", "en")["title"], "DNA · B double helix")

    def test_particle_spec_is_valid_and_rotation_is_equivalent(self):
        from agenti.particles import codec
        spec = exact.to_particles(exact.scene("dna", "it"))
        codec.validate(spec)
        self.assertLessEqual(len(spec["parts"]), 96)

        def apply_zyx(v, rx, ry, rz):
            x, y, z = v
            rx, ry, rz = (math.radians(d) for d in (rx, ry, rz))
            y, z = y * math.cos(rx) - z * math.sin(rx), y * math.sin(rx) + z * math.cos(rx)
            x, z = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
            x, y = x * math.cos(rz) - y * math.sin(rz), x * math.sin(rz) + y * math.cos(rz)
            return [x, y, z]

        def apply_xyz(v, rx, ry, rz):
            x, y, z = v
            rx, ry, rz = (math.radians(d) for d in (rx, ry, rz))
            x, y = x * math.cos(rz) - y * math.sin(rz), x * math.sin(rz) + y * math.cos(rz)
            x, z = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
            y, z = y * math.cos(rx) - z * math.sin(rx), y * math.sin(rx) + z * math.cos(rx)
            return [x, y, z]

        rot = [30.0, -50.0, 70.0]
        converted = exact._zyx(rot)
        for vector in ([1, 0, 0], [0, 1, 0], [0, 0, 1]):
            for a, b in zip(apply_xyz(vector, *rot), apply_zyx(vector, *converted)):
                self.assertAlmostEqual(a, b, places=3)

    def test_follow_uses_exact_scene_without_model_call(self):
        visual = {"reply": "x", "ui": {"mode": "face", "particles": {"concept": "dna"}}}
        with mock.patch("agenti.particles.store.store.lookup", return_value=None), \
                mock.patch.object(commands, "_show_particles") as shown, \
                mock.patch.object(commands, "background") as bg:
            commands.follow(visual, "fammi vedere come è fatto il DNA", "it")
        bg.assert_not_called()
        shown.assert_called_once()
        snap = session.snapshot()
        self.assertEqual(snap["source"], "exact")
        self.assertEqual(snap["status"], "ready")


class PrivilegesTest(unittest.TestCase):
    def request(self, scheme="http", host="127.0.0.1"):
        req = mock.Mock()
        req.url.scheme = scheme
        req.client.host = host
        req.cookies = {}
        req.headers = {}
        return req

    def test_owner_in_front_of_host_display_is_super_admin(self):
        from agenti.desktop import privileges
        with mock.patch.object(privileges, "_admin_session", return_value=False), \
                mock.patch.object(privileges, "_owner_in_front", return_value=True):
            self.assertTrue(privileges.is_super_admin(self.request(), 0.0))
        with mock.patch.object(privileges, "_admin_session", return_value=False), \
                mock.patch.object(privileges, "_owner_in_front", return_value=False), \
                mock.patch.object(privileges, "is_host_display", return_value=False):
            self.assertFalse(privileges.is_super_admin(self.request(host="192.168.1.20"), 0.0))

    def test_remote_needs_full_administrator(self):
        from agenti.desktop import privileges
        req = self.request("https", "192.168.1.20")
        with mock.patch.object(privileges, "session_user", return_value="nunzio"), \
                mock.patch.object(privileges, "account", return_value={"role": "administrator", "nodes": ["*"]}):
            self.assertTrue(privileges._admin_session(req))
        with mock.patch.object(privileges, "session_user", return_value="ospite"), \
                mock.patch.object(privileges, "account", return_value={"role": "operator", "nodes": ["*"]}):
            self.assertFalse(privileges._admin_session(req))
        from fastapi import HTTPException
        with mock.patch.object(privileges, "is_super_admin", return_value=False):
            with self.assertRaises(HTTPException):
                privileges.require_super_admin(req)


if __name__ == "__main__":
    unittest.main()
