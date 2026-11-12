import json
import random
import unittest
from unittest import mock

from agenti.desktop import audience_view, presence_bridge
from agenti.desktop.audience import Policy, Tracker, fuse
from state import store

OWNER = {"person": "nunzio", "authorized": True, "confidence": 0.9, "liveness": "live", "near": True}
STRANGER = {"person": None, "authorized": False, "confidence": 0.9, "liveness": "live", "near": True}
STAFF = {"person": "maria", "authorized": False, "confidence": 0.9, "liveness": "live", "near": False}


def seen(*faces, voices=()):
    return {"vision": "ok", "faces": [dict(f) for f in faces], "voices": list(voices)}


def voice(at_ms):
    return {"person": "nunzio", "authorized": True, "score": 0.8, "at_ms": at_ms}


def kind(signals, policy=Policy()):
    return fuse(signals, policy, 10_000).kind


class FusionTests(unittest.TestCase):

    def test_audience_kinds(self):
        self.assertEqual(kind(seen()), "empty")
        self.assertEqual(kind(seen(OWNER)), "authorized")
        self.assertEqual(kind(seen(STRANGER)), "guest_only")
        self.assertEqual(kind(seen(STAFF)), "guest_only")
        self.assertEqual(kind(seen(OWNER, STRANGER)), "mixed")

    def test_a_photo_of_the_owner_opens_nothing(self):
        self.assertEqual(kind(seen({**OWNER, "liveness": "spoof"})), "guest_only")
        self.assertEqual(kind(seen({**OWNER, "liveness": "unknown"})), "uncertain")
        self.assertEqual(kind(seen({**OWNER, "liveness": "unknown"}), Policy(require_liveness=False)), "authorized")

    def test_voice_corroborates_and_strengthens(self):
        self.assertEqual(kind(seen({**OWNER, "liveness": "unknown"}, voices=[voice(9_000)])), "authorized")
        reading = fuse(seen(OWNER, voices=[voice(9_500)]), Policy(), 10_000)
        self.assertEqual(reading.members[0]["proof"], "strong")

    def test_bad_values_fail_closed(self):
        self.assertEqual(kind(seen({**OWNER, "confidence": float("nan")})), "uncertain")
        self.assertEqual(kind(seen({**OWNER, "confidence": "x"})), "uncertain")
        self.assertEqual(kind(seen(voices=[voice(0), voice(60_000)])), "empty")
        self.assertEqual(kind({"vision": "offline", "faces": [OWNER]}), "uncertain")
        self.assertEqual(kind({}), "uncertain")
        self.assertEqual(kind({"vision": "disabled"}), "authorized")


class TrackerTests(unittest.TestCase):

    def test_opening_waits_and_closing_is_immediate(self):
        t = Tracker(Policy(), 0)
        self.assertEqual(t.step(seen(), 0)["kind"], "empty")
        self.assertEqual(t.step(seen(OWNER), 100)["kind"], "empty")
        self.assertEqual(t.step(seen(OWNER), 1_300)["kind"], "authorized")
        mixed = t.step(seen(OWNER, STRANGER), 1_310)
        self.assertEqual((mixed["kind"], mixed["since_ms"]), ("mixed", 1_310))
        self.assertEqual(t.step(seen(OWNER), 2_000)["kind"], "mixed")
        self.assertEqual(t.step(seen(OWNER), 3_300)["kind"], "authorized")

    def test_away_and_voice_hold(self):
        t = Tracker(Policy(), 0)
        t.step(seen(OWNER), 0)
        t.step(seen(OWNER), 1_500)
        self.assertEqual(t.step(seen(), 5_000)["kind"], "authorized")
        self.assertTrue(t.step(seen(), 11_600)["nucleus_only"])
        t = Tracker(Policy(), 0)
        t.step(seen(OWNER), 0)
        t.step(seen(OWNER), 1_500)
        self.assertEqual(t.step(seen(voices=[voice(2_000)]), 2_000)["kind"], "authorized")
        self.assertEqual(t.step(seen(), 25_000)["kind"], "authorized")
        self.assertEqual(t.step(seen(), 33_000)["kind"], "empty")

    def test_camera_fault_closes_at_once(self):
        t = Tracker(Policy(), 0)
        t.step(seen(OWNER), 0)
        t.step(seen(OWNER), 1_500)
        self.assertEqual(t.step({"vision": "offline"}, 1_600)["kind"], "uncertain")

    def test_guest_identities_are_never_reported(self):
        out = Tracker(Policy(), 0).step(seen(STRANGER, STAFF), 0)
        self.assertEqual((out["members"], out["guests"]), ([], 2))


def _native():
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "RustPresenceTracker", None)


@unittest.skipUnless(_native(), "motore nativo non installato")
class NativeParityTests(unittest.TestCase):

    def test_rust_and_python_agree_on_random_sequences(self):
        rng = random.Random(7)
        pool = [OWNER, STRANGER, STAFF, {**OWNER, "liveness": "unknown"}, {**OWNER, "liveness": "spoof"},
                {**OWNER, "confidence": 0.3}]
        for _ in range(40):
            policy = Policy(require_liveness=rng.random() < 0.7)
            native = presence_bridge.NativeTracker(_native()(json.dumps(policy.as_dict()), 0))
            python, now = Tracker(policy, 0), 0
            for _ in range(60):
                now += rng.choice((50, 300, 900, 4_000, 12_000))
                vision = rng.choice(("ok", "ok", "ok", "ok", "offline", "disabled"))
                faces = rng.sample(pool, rng.randint(0, 3))
                voices = [voice(max(0, now - rng.randint(0, 15_000)))] if rng.random() < 0.3 else []
                signals = {"vision": vision, "faces": faces, "voices": voices}
                self.assertEqual(native.step(signals, now), python.step(signals, now))


class VisibilityTests(unittest.TestCase):

    def test_truth_table(self):
        show_all = {"guest_public": True, "trust_guests": True}
        cases = [
            ("authorized", "sensitive", {}, True),
            ("mixed", "public", {}, True),
            ("mixed", "household", {}, False),
            ("mixed", "household", show_all, True),
            ("mixed", "personal", show_all, False),
            ("guest_only", "public", {}, False),
            ("guest_only", "public", show_all, True),
            ("guest_only", "household", show_all, False),
            ("empty", "public", show_all, False),
            ("uncertain", "public", show_all, False),
        ]
        for k, level, show, expected in cases:
            self.assertEqual(audience_view.visible(k, level, True, False, show), expected, (k, level, show))
        self.assertFalse(audience_view.visible("guest_only", "public", False, False, show_all))

    def test_public_alerts_always_show(self):
        for k in ("empty", "guest_only", "mixed", "authorized", "uncertain"):
            self.assertTrue(audience_view.visible(k, "public", False, True, {}))
        self.assertFalse(audience_view.visible("mixed", "personal", False, True, {}))

    def test_redaction_keeps_only_the_nucleus_for_guests(self):
        snap = {"desk": [{"id": "health", "personal": True}, {"id": "clock", "guest_safe": True},
                         {"id": "alarm", "urgent": True}],
                "presence": {"status": "ok", "people": [{"slug": "nunzio", "name": "Nunzio", "known": True, "near": True,
                                                         "vitals": {"hr": 70}, "gaze": {"x": 0.5, "y": 0.5}}]},
                "logs": ["Saluto: Buongiorno Nunzio"], "home": {"locks": 1}, "agency": {"x": 1},
                "live_dialogue": {"reply": "ciao"}}
        guests = audience_view.redact(snap, {"kind": "guest_only"}, {"guest_public": False})
        self.assertEqual([i["id"] for i in guests["desk"]], ["alarm"])
        self.assertEqual(guests["presence"]["people"], [{"known": False, "near": True, "gaze": {"x": 0.5, "y": 0.5}}])
        self.assertEqual((guests["logs"], guests["home"], guests["agency"]), ([], None, None))
        self.assertEqual(guests["live_dialogue"], {"reply": "ciao"})
        empty = audience_view.redact(snap, {"kind": "empty"}, {})
        self.assertIsNone(empty["live_dialogue"])
        mixed = audience_view.redact(snap, {"kind": "mixed"}, {})
        self.assertEqual([i["id"] for i in mixed["desk"]], ["clock", "alarm"])
        self.assertIs(audience_view.redact(snap, {"kind": "authorized"}, {}), snap)
        self.assertEqual(len(snap["desk"]), 3)

    def test_unknown_audience_is_restrictive(self):
        out = audience_view.redact({"desk": [{"id": "clock"}]}, {}, {})
        self.assertEqual(out["desk"], [])


class BridgeTests(unittest.TestCase):

    def setUp(self):
        self.saved = (store.presence, store.audience)

    def tearDown(self):
        store.presence, store.audience = self.saved

    def test_face_signals_drop_names_and_map_roles(self):
        face = presence_bridge.face_signal({"slug": "nunzio", "known": True, "role": "owner", "confidence": 0.8,
                                            "liveness": {"state": "live", "score": 0.9}, "near": True, "name": "Nunzio"})
        self.assertEqual(face, {"person": "nunzio", "authorized": True, "confidence": 0.8, "liveness": "live", "near": True})
        guest = presence_bridge.face_signal({"slug": "maria", "known": True, "role": "staff", "liveness": {"state": "weird"}})
        self.assertEqual((guest["authorized"], guest["liveness"]), (False, "unknown"))

    def test_stale_vision_is_offline(self):
        self.assertEqual(presence_bridge._vision_state({"status": "ok"}, 0.0, 100.0), "offline")
        self.assertEqual(presence_bridge._vision_state({"status": "ok"}, 99.0, 100.0), "ok")
        self.assertEqual(presence_bridge._vision_state({"status": "disabled"}, 0.0, 100.0), "disabled")
        self.assertEqual(presence_bridge._vision_state({"status": "starting"}, 99.0, 100.0), "offline")

    def test_update_publishes_only_the_kind(self):
        bridge = presence_bridge.PresenceBridge(clock=lambda: 1000.0)
        signals = {"vision": "ok", "faces": [STRANGER], "voices": []}
        with mock.patch.object(presence_bridge, "gate_enabled", return_value=True), \
                mock.patch.object(presence_bridge, "_native_class", return_value=None), \
                mock.patch.object(presence_bridge, "_require_liveness", return_value=True), \
                mock.patch.object(bridge, "signals", return_value=signals):
            bridge.update()
        self.assertEqual(store.audience["kind"], "guest_only")
        self.assertTrue(store.audience["nucleus_only"])
        self.assertNotIn("members", store.audience)

    def run_with_native(self, native):
        bridge = presence_bridge.PresenceBridge(clock=lambda: 1000.0)
        signals = {"vision": "ok", "faces": [STRANGER], "voices": []}
        with mock.patch.object(presence_bridge, "gate_enabled", return_value=True), \
                mock.patch.object(presence_bridge, "_native_class", return_value=native), \
                mock.patch.object(presence_bridge, "_require_liveness", return_value=True), \
                mock.patch.object(bridge, "signals", return_value=signals), \
                self.assertLogs("nuxiva.desktop.presence", "WARNING"):
            result = bridge.update()
        self.assertIsInstance(bridge.tracker, Tracker)
        return result

    def test_outdated_native_schema_falls_back_to_python(self):
        def outdated(policy_json, now_ms):
            raise ValueError("unknown field `continuity_ms`")
        self.assertEqual(self.run_with_native(outdated)["kind"], "guest_only")

    def test_native_step_failure_falls_back_to_python(self):
        class Broken:
            def __init__(self, policy_json, now_ms):
                pass

            def step(self, signals_json, now_ms):
                raise ValueError("unknown field `near`")
        self.assertEqual(self.run_with_native(Broken)["kind"], "guest_only")

    def test_disabled_gate_is_authorized(self):
        bridge = presence_bridge.PresenceBridge(clock=lambda: 1000.0)
        with mock.patch.object(presence_bridge, "gate_enabled", return_value=False):
            self.assertEqual(bridge.update()["kind"], "authorized")

    def test_advisory_webcam_recognition_stays_authorized_after_greeting(self):
        from agenti.people.presence import monitor
        now = [1000.0]
        bridge = presence_bridge.PresenceBridge(clock=lambda: now[0])
        bridge.roles["nunzio"] = ("owner", 1000.0)
        store.presence = {"status": "ok", "people": [{"slug": "nunzio", "name": "Nunzio Aprile", "known": True,
                                                      "role": "owner", "confidence": 0.88,
                                                      "liveness": {"state": "unknown"}, "near": True}]}
        store.greeting = {"id": 1, "text": "Buongiorno, Nunzio Aprile.", "names": ["Nunzio Aprile"],
                          "slug": "nunzio", "at": 1000.0}
        with mock.patch.object(presence_bridge, "gate_enabled", return_value=True), \
                mock.patch.object(presence_bridge, "_require_liveness", return_value=False), \
                mock.patch.object(monitor, "updated_at", 1000.0):
            bridge.update()
            for step_s in (1.5, 4.0, 8.0, 12.0):
                now[0] = 1000.0 + step_s
                monitor.updated_at = now[0]
                res = bridge.update()
                self.assertEqual(res["kind"], "authorized")
                self.assertFalse(res["nucleus_only"])

    def test_sensitive_items_require_double_permission(self):
        self.assertTrue(audience_view.requires_double_permission({"id": "vault", "data": {}}))
        self.assertTrue(audience_view.requires_double_permission({"id": "note", "data": {"text": "IBAN IT60X0542811101000000123456"}}))
        self.assertTrue(audience_view.requires_double_permission({"id": "note", "data": {"text": "password segreta"}}))
        self.assertEqual(audience_view.sensitivity({"id": "note", "data": {"text": "conto corrente"}}), "sensitive")
        self.assertFalse(audience_view.requires_double_permission({"id": "weather", "data": {"temp": 22}}))


class DeskGateTests(unittest.TestCase):

    def setUp(self):
        from config import write_env
        from agenti.desktop import desk as desk_module
        write_env({"NUXIVA_PRIVACY_AUTOCLOSE": "1", "NUXIVA_DISPLAY_PRESENCE_GATE": "1"})
        self.addCleanup(lambda: write_env({"NUXIVA_DISPLAY_PRESENCE_GATE": "1"}))
        self.saved = (store.presence, store.audience, store.privacy)
        self.desk = desk_module.Desk()
        self.desk.scan()
        self.desk.show("g_notify", {"x": 1})
        self.desk.show("weather", {"x": 1})

    def tearDown(self):
        store.presence, store.audience, store.privacy = self.saved

    def sweep(self, audience):
        with mock.patch.object(presence_bridge.bridge, "update", return_value=audience):
            return self.desk.sweep_private()

    def test_a_guest_closes_personal_widgets_at_once(self):
        self.assertFalse(self.sweep({"kind": "authorized", "nucleus_only": False}))
        self.assertTrue(self.sweep({"kind": "mixed", "nucleus_only": False}))
        self.assertEqual({i["id"] for i in self.desk.instances.values()}, {"weather"})
        self.assertFalse(store.privacy["away"])

    def test_nobody_authorized_means_away_for_the_display(self):
        self.assertTrue(self.sweep({"kind": "uncertain", "nucleus_only": True}))
        self.assertTrue(store.privacy["away"])


if __name__ == "__main__":
    unittest.main()
