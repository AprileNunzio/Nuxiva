import json
import random
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from features.authz import access, capmap, gate, guard, matrix_store, texts
from features.authz.access import COLUMNS, Matrix, MatrixError, PythonEngine
from features.authz.principal import ANONYMOUS, Principal, Strength, act_as, current
from features.authz.risk import compose, forget
from state import store

ROOT = Path(__file__).resolve().parents[2]
RUST_COPY = ROOT / "native" / "crates" / "access-core" / "src" / "matrix" / "default.json"
ENTITIES = {
    "light.salotto": {"entity_id": "light.salotto", "domain": "light"},
    "lock.luce_porta": {"entity_id": "lock.luce_porta", "domain": "lock"},
    "cover.garage": {"entity_id": "cover.garage", "domain": "cover", "device_class": "garage"},
}
GUEST = Principal(slug="", role="guest", strength=Strength.NONE)
OWNER = Principal(slug="nunzio", role="owner", strength=Strength.STRONG)
STAFF = Principal(slug="maria", role="staff", strength=Strength.STRONG)
FAMILY = Principal(slug="anna", role="family", strength=Strength.SINGLE)


def lookup(entity_id):
    return ENTITIES.get(entity_id)


class MatrixTests(unittest.TestCase):

    def test_python_and_rust_share_the_same_default_matrix(self):
        if not RUST_COPY.exists():
            self.skipTest("sorgenti Rust assenti")
        self.assertEqual(json.loads(RUST_COPY.read_text()), json.loads(access.DEFAULT_FILE.read_text()))

    def test_every_cell_has_a_positive_and_a_negative_case(self):
        engine = PythonEngine()
        for key, cells in engine.matrix.export().items():
            if "*" in key:
                continue
            for role, cell in zip(COLUMNS, cells):
                best = engine.decide([key], role, "strong", True, True)
                worst = engine.decide([key], role, "none", False, False)
                expected = {"allow": (("allow", ""), ("allow", "")), "confirm": (("confirm", ""), ("proof", "single"))}
                if cell in expected:
                    self.assertEqual((best, worst), expected[cell], (key, role))
                elif cell == "deny":
                    self.assertEqual((best[0], worst[0]), ("deny", "deny"), (key, role))
                else:
                    self.assertEqual(best, ("allow", ""), (key, role))
                    self.assertNotEqual(worst[0], "allow", (key, role))

    def test_overrides_cannot_open_the_floors(self):
        relaxed = json.loads(access.DEFAULT_FILE.read_text())
        relaxed["rules"] = {k: ["allow"] * 6 for k in relaxed["rules"]}
        relaxed["rules"]["home.*"] = ["allow"] * 6
        engine = PythonEngine(json.dumps(relaxed))
        for cap in ("home.lock.unlock", "home.alarm.disarm", "comm.message.send", "people.health.read"):
            self.assertEqual(engine.decide([cap], "guest", "strong", True, True)[0], "deny", cap)
            self.assertEqual(engine.decide([cap], "anonymous", "strong", True, True)[0], "deny", cap)
        self.assertEqual(engine.decide(["home.lock.unlock"], "owner", "single"), ("proof", "strong"))

    def test_malformed_matrices_are_rejected(self):
        for raw in ("{}", "[]", "nope", '{"version":2,"rules":{"risk.critical":["deny","deny","deny","deny","deny","deny"]}}',
                    '{"version":1,"rules":{"home.light.set":["allow","allow","allow","allow","allow","allow"]}}',
                    '{"version":1,"rules":{"risk.critical":["deny"]}}',
                    '{"version":1,"rules":{"risk.critical":["deny","deny","deny","deny","deny","x"]}}',
                    '{"version":1,"rules":{"risk.critical":["deny","deny","deny","deny","deny","deny"],"BAD":["deny","deny","deny","deny","deny","deny"]}}'):
            with self.assertRaises(MatrixError, msg=raw):
                Matrix.parse(raw)
        with self.assertRaises(MatrixError):
            PythonEngine().decide(["NOT VALID"], "owner", "strong")


def _native():
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "RustAccessMatrix", None)


@unittest.skipUnless(_native(), "motore nativo non installato")
class NativeParityTests(unittest.TestCase):

    def test_rust_and_python_agree(self):
        rng = random.Random(11)
        rust, python = _native()(None), PythonEngine()
        caps = list(python.matrix.export()) + ["zzz.unknown.cap", "home.lock.thing", "media.other"]
        caps = [c for c in caps if "*" not in c]
        roles = list(COLUMNS) + ["system", "friend", "service", "intruder"]
        self.assertEqual(json.loads(rust.export()), json.loads(python.export()))
        for _ in range(3000):
            chosen = rng.sample(caps, rng.randint(0, 3))
            args = (chosen, rng.choice(roles), rng.choice(access.STRENGTHS), rng.choice((None, True, False)),
                    rng.random() < 0.5)
            self.assertEqual(rust.decide(*args), python.decide(*args), args)


class CapabilityMapTests(unittest.TestCase):

    def caps(self, domain, service, entity, **data):
        return capmap.ha_service({"domain": domain, "service": service, "entity_id": entity, **data}, lookup)

    def test_home_assistant_calls(self):
        self.assertEqual(self.caps("light", "turn_on", "light.salotto"), ["home.light.set"])
        self.assertEqual(self.caps("cover", "open_cover", "cover.garage"), ["home.gate.open"])
        self.assertEqual(self.caps("climate", "set_temperature", "climate.casa", temperature=21), ["home.climate.adjust"])
        self.assertEqual(self.caps("climate", "set_temperature", "climate.casa", temperature=30), ["home.climate.set"])
        self.assertEqual(self.caps("qualcosa", "turn_on", ""), ["risk.critical"])

    def test_a_disguised_name_does_not_hide_a_lock(self):
        self.assertEqual(self.caps("light", "turn_on", "lock.luce_porta"), ["home.light.set", "home.lock.unlock"])

    def test_tools_and_composites(self):
        self.assertEqual(capmap.of_call("music_play", {}), ["media.music.play"])
        self.assertEqual(capmap.of_call("person_profile", {}), ["people.profile.read"])
        self.assertEqual(capmap.of_call("now", {}), ["risk.info"])
        compose("scherzo", ["music_play", "send_email"])
        self.addCleanup(forget, "scherzo")
        self.assertEqual(capmap.of_call("scherzo", {}), ["risk.critical"])


class GateTests(unittest.TestCase):

    def setUp(self):
        guard.throttle.reset()
        self.saved = store.audience
        patcher = mock.patch("features.authz.capability.ha_lookup", side_effect=lookup)
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        current.set(ANONYMOUS)
        store.audience = self.saved
        guard.throttle.reset()

    def decide(self, who, name, args=None):
        act_as(who)
        return gate.tool(name, args or {})

    def test_guest_gets_music_and_lights(self):
        self.assertTrue(self.decide(GUEST, "music_play", {"query": "jazz"}).allowed)
        self.assertTrue(self.decide(GUEST, "ha_call_service", {"domain": "light", "service": "turn_on",
                                                               "entity_id": "light.salotto"}).allowed)

    def test_guest_is_refused_neutrally(self):
        for name, args in (("ha_call_service", {"domain": "lock", "service": "unlock", "entity_id": "lock.luce_porta"}),
                           ("person_profile", {"slug": "nunzio"}), ("send_email", {}), ("read_file", {})):
            decision = self.decide(GUEST, name, args)
            self.assertFalse(decision.allowed, name)
        self.assertEqual(gate.refusal(self.decide(GUEST, "person_profile", {})), texts.say("refusal.guest"))

    def test_roles(self):
        unlock = {"domain": "lock", "service": "unlock", "entity_id": "lock.luce_porta"}
        self.assertTrue(self.decide(OWNER, "ha_call_service", unlock).allowed)
        self.assertFalse(self.decide(STAFF, "ha_call_service", unlock).allowed)
        self.assertFalse(self.decide(Principal(slug="leo", role="family", subrole="child", strength=Strength.STRONG),
                                     "ha_call_service", {"domain": "lock", "service": "lock", "entity_id": "lock.luce_porta"}).allowed)

    def test_unknown_voice_is_guest_or_anonymous_by_audience(self):
        store.audience = {"kind": "mixed"}
        self.assertEqual(guard.speaker_role(ANONYMOUS), "guest")
        store.audience = {"kind": "empty"}
        self.assertEqual(guard.speaker_role(ANONYMOUS), "anonymous")
        self.assertEqual(guard.speaker_role(Principal(slug="x", role="guest")), "guest")

    def test_personal_data_follows_ownership(self):
        act_as(FAMILY)
        self.assertTrue(guard.own(FAMILY, {"slug": "anna"}))
        self.assertFalse(guard.own(FAMILY, {"slug": "nunzio"}))
        self.assertEqual(guard.decide(FAMILY, ["people.health.read"], 2, {"slug": "nunzio"}).code, "owner_data")

    def test_outsiders_are_rate_limited_on_actions_only(self):
        light = {"domain": "light", "service": "turn_on", "entity_id": "light.salotto"}
        with mock.patch.object(guard, "rate", return_value=3):
            results = [self.decide(GUEST, "ha_call_service", light).allowed for _ in range(4)]
            self.assertEqual(results, [True, True, True, False])
            self.assertEqual(self.decide(GUEST, "ha_call_service", light).code, "rate")
            self.assertTrue(self.decide(GUEST, "now").allowed)

    def test_family_automation_needs_confirmation(self):
        act_as(FAMILY)
        self.assertTrue(gate.confirm_required("run_automation", {"id": "notte"}))
        act_as(OWNER)
        self.assertFalse(gate.confirm_required("run_automation", {"id": "notte"}))

    def test_voice_plans_use_capabilities(self):
        act_as(GUEST)
        plan = {"kind": "command", "calls": [{"domain": "cover", "service": "open_cover", "entity_ids": ["cover.garage"]}]}
        self.assertFalse(gate.plan(plan, "apri il garage", lookup).allowed)


class StoreTests(unittest.TestCase):

    def setUp(self):
        folder = Path(tempfile.mkdtemp())
        self.paths = {"FOLDER": folder, "MATRIX_FILE": folder / "matrix.json", "SIGNATURE_FILE": folder / "matrix.sig",
                      "KEY_FILE": folder / "matrix.key"}
        for name, value in self.paths.items():
            patcher = mock.patch.object(matrix_store, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.store = matrix_store.AccessStore()

    def custom(self):
        data = json.loads(access.DEFAULT_FILE.read_text())
        data["rules"]["media.game.play"] = ["allow", "allow", "allow", "allow", "deny", "deny"]
        return data

    def test_saved_matrices_are_signed_and_private(self):
        self.assertEqual(self.store.save(self.custom())["source"], "custom")
        self.assertEqual(stat.S_IMODE(self.paths["KEY_FILE"].stat().st_mode), 0o600)
        self.assertEqual(self.store.decide(["media.game.play"], "guest", "none", None, False), ("deny", "guest"))
        fresh = matrix_store.AccessStore()
        fresh.load()
        self.assertEqual(fresh.source, "custom")

    def test_a_tampered_matrix_falls_back_to_the_default(self):
        self.store.save(self.custom())
        raw = self.paths["MATRIX_FILE"].read_text().replace('"deny"', '"allow"')
        self.paths["MATRIX_FILE"].write_text(raw)
        with self.assertLogs("nuxiva.authz.matrix", "ERROR"):
            self.store.load()
        self.assertEqual(self.store.source, "builtin")
        self.assertEqual(self.store.decide(["home.lock.unlock"], "guest", "strong", None, True)[0], "deny")

    def test_preview_reports_changes_and_hardened_cells(self):
        data = self.custom()
        data["rules"]["home.lock.unlock"] = ["allow"] * 6
        with mock.patch.object(matrix_store, "store", self.store):
            report = self.store.preview(data)
        self.assertIn({"capability": "media.game.play", "role": "guest", "before": "allow", "after": "deny"},
                      report["changes"])
        self.assertIn({"capability": "home.lock.unlock", "role": "guest", "asked": "allow", "kept": "deny"},
                      report["hardened"])

    def test_reset_restores_the_default(self):
        self.store.save(self.custom())
        self.assertEqual(self.store.reset()["source"], "builtin")


class TextsTests(unittest.TestCase):

    def test_refusals_exist_in_every_language(self):
        for lang in ("it", "en", "fr"):
            for code in gate.NEUTRAL:
                self.assertNotEqual(texts.say(f"refusal.{code}", lang), f"refusal.{code}", (lang, code))


if __name__ == "__main__":
    unittest.main()
