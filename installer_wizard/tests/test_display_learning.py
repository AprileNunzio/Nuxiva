import asyncio
import json
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import HTTPException

from agenti.desktop import learner_bridge, learner_store, learning_api
from agenti.desktop.learner_bridge import LearnerBridge, audience_of, context_vector


def _native():
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "RustLearner", None)


class Clock:

    def __init__(self, t: float = 1_800_000_000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


class TempState(unittest.TestCase):

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        patcher = mock.patch.object(learner_store, "STATE_DIR", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)


class StoreTests(TempState):

    def test_the_master_key_is_private_and_stable(self):
        key = learner_store.master()
        path = self.root / "display_learner" / "master.key"
        self.assertEqual(len(key), 32)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(learner_store.master(), key)

    def test_pseudonyms_hide_the_name_and_depend_on_the_key(self):
        a = learner_store.pseudonym("Nunzio", b"k" * 32)
        self.assertEqual(a, learner_store.pseudonym("nunzio", b"k" * 32))
        self.assertNotEqual(a, learner_store.pseudonym("nunzio", b"j" * 32))
        self.assertNotIn("nunzio", a)
        self.assertRegex(a, r"^[0-9a-f]{64}$")

    def test_profiles_are_saved_privately_and_deleted(self):
        person = "ab" * 32
        learner_store.save(person, b"sealed")
        path = self.root / "display_learner" / "profiles" / f"{person}.bin"
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(learner_store.stored(), [(person, b"sealed")])
        self.assertTrue(learner_store.delete(person))
        self.assertFalse(learner_store.delete(person))

    def test_paths_cannot_escape_the_folder(self):
        for bad in ("../../etc/passwd", "AB" * 32, "x"):
            with self.assertRaises(ValueError):
                learner_store.save(bad, b"x")


class PureLogicTests(unittest.TestCase):

    def test_only_one_authorized_person_is_attributed(self):
        self.assertEqual(audience_of({"kind": "authorized", "members": [{"person": "anna"}], "guests": 0}),
                         (True, "anna", False, 1))
        self.assertEqual(audience_of({"kind": "authorized", "members": [{"person": "a"}, {"person": "b"}]}),
                         (False, None, False, 2))
        self.assertEqual(audience_of({"kind": "mixed", "members": [{"person": "a"}], "guests": 1}), (True, None, True, 2))
        self.assertEqual(audience_of({"kind": "guest_only", "members": [], "guests": 2}), (True, None, True, 2))
        self.assertEqual(audience_of({"kind": "empty"})[0], False)
        self.assertEqual(audience_of({"kind": "uncertain"})[0], False)

    def test_context_is_coarse(self):
        ctx = context_vector(1_800_000_000.0, 2, "project", 5, [{"id": "music"}])
        self.assertEqual(set(ctx), {"band", "weekend", "activity", "crowd", "role"})
        self.assertIn(ctx["band"], range(6))
        self.assertEqual((ctx["activity"], ctx["crowd"], ctx["role"]), ("project", 2, "side"))
        self.assertEqual(context_vector(1_800_000_000.0, 0, "ambient", 1, [{"id": "music"}])["activity"], "media")


class WithoutNativeTests(unittest.TestCase):

    def test_the_planner_keeps_neutral_preferences(self):
        bridge = LearnerBridge()
        with mock.patch.object(learner_bridge, "_native_class", return_value=None):
            self.assertIsNone(bridge.ready())
            self.assertEqual(bridge.preferences(["weather"], 0, "ambient", [], 1.0), {})
            bridge.observe_desk([{"key": "weather", "id": "weather"}], 1.0)
            self.assertFalse(bridge.interacted("weather"))
            self.assertEqual(bridge.metrics()["engine"], "missing")

    def test_the_switch_turns_learning_off(self):
        bridge = LearnerBridge()
        with mock.patch.object(learner_bridge, "enabled", return_value=False):
            self.assertIsNone(bridge.ready())


class FeedbackApiTests(unittest.TestCase):

    def request(self, body):
        request = mock.Mock()

        async def read():
            return body
        request.json = read
        return request

    def call(self, body):
        with mock.patch.object(learning_api, "require_display"):
            return asyncio.run(learning_api.display_feedback(self.request(body)))

    def test_bad_batches_are_refused(self):
        for body in ({"events": "x"}, {"events": [{"key": "a"}] * 33}, {"events": ["x"]}, []):
            with self.assertRaises(HTTPException):
                self.call(body)

    def test_only_browser_kinds_are_accepted(self):
        with mock.patch.object(learner_bridge.bridge, "interacted", side_effect=lambda k, kind: kind == "interact") as hit:
            reply = self.call({"events": [{"key": "w", "kind": "interact"}, {"key": "w", "kind": "ask_show"}]})
        self.assertEqual(reply["accepted"], 1)
        self.assertEqual(hit.call_count, 2)

    def test_person_names_are_validated(self):
        with self.assertRaises(HTTPException):
            asyncio.run(learning_api.display_learning_reset("../x", "admin"))


@unittest.skipUnless(_native(), "motore nativo non installato")
class NativeLearnerTests(TempState):

    def setUp(self):
        super().setUp()
        self.clock = Clock()
        self.bridge = LearnerBridge(clock=self.clock)
        self.who = mock.patch.object(learner_bridge, "audience_of", return_value=(True, "anna", False, 1))
        self.who.start()
        self.addCleanup(self.who.stop)

    def show_and_close(self, rounds: int):
        for n in range(rounds):
            key = f"weather:{n}"
            self.bridge.observe_desk([{"key": key, "id": "weather"}])
            self.clock.t += 1
            self.bridge.closed(key)
            self.bridge.observe_desk([])
            self.clock.t += 60

    def test_quick_closes_lower_the_preference(self):
        self.show_and_close(40)
        prefs = self.bridge.preferences(["weather", "clock"], 0, "ambient", [], self.clock.t)
        self.assertLess(prefs["weather"], -0.1)
        self.assertGreaterEqual(prefs["weather"], -0.3)
        self.assertAlmostEqual(prefs["clock"], 0.0)

    def test_safety_widgets_are_never_penalised(self):
        for n in range(30):
            self.bridge.observe_desk([{"key": f"alarm:{n}", "id": "alarm"}])
            self.clock.t += 1
            self.bridge.closed(f"alarm:{n}")
            self.bridge.observe_desk([])
        self.assertAlmostEqual(self.bridge.preferences(["alarm"], 0, "ambient", [], self.clock.t)["alarm"], 0.0)

    def test_profiles_are_sealed_on_disk_and_reload(self):
        self.show_and_close(20)
        self.bridge.flush()
        files = list((self.root / "display_learner" / "profiles").glob("*.bin"))
        self.assertEqual(len(files), 1)
        self.assertNotIn(b"weather", files[0].read_bytes())
        self.assertNotIn("anna", files[0].name)
        fresh = LearnerBridge(clock=self.clock)
        before = self.bridge.preferences(["weather"], 0, "ambient", [], self.clock.t)["weather"]
        after = fresh.preferences(["weather"], 0, "ambient", [], self.clock.t)["weather"]
        self.assertAlmostEqual(before, after, places=5)

    def test_reset_forgets_and_deletes(self):
        self.show_and_close(20)
        self.bridge.flush()
        self.assertTrue(self.bridge.reset("anna"))
        self.assertEqual(list((self.root / "display_learner" / "profiles").glob("*.bin")), [])
        self.assertAlmostEqual(self.bridge.preferences(["weather"], 0, "ambient", [], self.clock.t)["weather"], 0.0)

    def test_a_tampered_profile_is_quarantined(self):
        self.show_and_close(5)
        self.bridge.flush()
        path = next((self.root / "display_learner" / "profiles").glob("*.bin"))
        path.write_bytes(path.read_bytes()[:-1] + b"\x00")
        fresh = LearnerBridge(clock=self.clock)
        with self.assertLogs("nuxiva.desktop.learner", "ERROR"):
            fresh.ready()
        self.assertTrue(path.with_suffix(".corrupt").exists())

    def test_guests_are_never_written_to_disk(self):
        self.who.stop()
        with mock.patch.object(learner_bridge, "audience_of", return_value=(True, None, True, 2)):
            self.show_and_close(10)
            self.bridge.flush()
        self.assertFalse((self.root / "display_learner" / "profiles").exists())
        self.who.start()

    def test_metrics_report_rates(self):
        self.show_and_close(4)
        data = self.bridge.metrics("anna")
        self.assertEqual(data["engine"], "rust")
        self.assertEqual(json.loads(json.dumps(data))["rates"]["quick_close"], 1.0)


if __name__ == "__main__":
    unittest.main()
