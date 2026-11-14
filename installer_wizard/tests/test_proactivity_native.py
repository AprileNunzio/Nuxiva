import json
import unittest

from agenti.autonomy import proactivity, proactivity_bridge
from agenti.autonomy.proactivity_py import PyProactivity

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "RustProactivity")
DAY = 1_699_920_000_000
HOUR = 3_600_000
MIN = 60_000


def ctx(situation="idle", present=(), guests=False, voice=False):
    return json.dumps({"situation": situation, "voice_free": voice, "guests_present": guests, "present": list(present), "tz_offset_min": 0})


def sig(domain, key, person=None, subject="", value=0, at=0):
    return proactivity.signal(domain, key, person, subject, value, at)


class Common:
    def make(self):
        raise NotImplementedError

    def go(self, store, domain, key, person=None, subject="", value=0, at=0, c=None):
        return json.loads(store.ingest(sig(domain, key, person, subject, value, at), c or ctx(present=[person] if person else []), at))

    def home(self, store, person, at):
        self.go(store, "presence", "home", person, "", 1, at, ctx(present=[person]))

    def test_meeting_becomes_a_widget_proposal_with_a_valid_task(self):
        store = self.make()
        now = DAY + 12 * HOUR
        self.home(store, "anna", now)
        out = self.go(store, "calendar", "event_in_minutes", "anna", "standup", 10, now + 1)
        self.assertEqual(out[0]["mode"], "widget")
        self.assertEqual(out[0]["action"]["input_ref"], "event:standup")
        self.assertEqual(out[0]["confidence"], 800)
        self.assertEqual(out[0]["explanation"]["reasons"][0]["code"], "proactive.why.conditions")
        self.assertEqual(len(json.loads(store.pending())), 1)
        self.assertEqual(json.loads(store.explain(out[0]["id"]))["origin"], "signal")

    def test_unmet_condition_is_ignored(self):
        store = self.make()
        now = DAY + 12 * HOUR
        self.assertEqual(self.go(store, "calendar", "event_in_minutes", "anna", "standup", 10, now), [])

    def test_voice_only_when_free_and_idle(self):
        store = self.make()
        now = DAY + 12 * HOUR
        self.home(store, "anna", now)
        out = self.go(store, "calendar", "event_in_minutes", "anna", "a", 5, now + 1, ctx(present=["anna"], voice=True))
        self.assertEqual(out[0]["mode"], "speak")

    def test_duplicates_and_quiet_hours(self):
        store = self.make()
        now = DAY + 12 * HOUR
        self.home(store, "anna", now)
        self.assertEqual(len(self.go(store, "calendar", "event_in_minutes", "anna", "s", 10, now + 1)), 1)
        self.assertEqual(self.go(store, "calendar", "event_in_minutes", "anna", "s", 10, now + 2), [])
        night = DAY + 23 * HOUR
        self.home(store, "anna", night)
        out = self.go(store, "calendar", "event_in_minutes", "anna", "late", 10, night + 1)
        self.assertTrue(out[0]["deferred"])
        self.assertEqual(out[0]["explanation"]["reasons"][-1]["code"], "proactive.why.quiet_hours")

    def test_conversation_defers_then_tick_releases(self):
        store = self.make()
        now = DAY + 12 * HOUR
        self.home(store, "anna", now)
        out = self.go(store, "calendar", "event_in_minutes", "anna", "s", 10, now + 1, ctx("conversation", ["anna"], voice=True))
        self.assertEqual((out[0]["mode"], out[0]["deferred"]), ("diary", True))
        self.assertEqual(json.loads(store.tick(ctx("conversation", ["anna"]), now + MIN)), [])
        back = json.loads(store.tick(ctx(present=["anna"]), now + 2 * MIN))
        self.assertEqual(back[0]["mode"], "widget")

    def test_private_health_blocked_with_guests_then_released_alone(self):
        store = self.make()
        now = DAY + 12 * HOUR
        crowd = ctx("guests", ["anna"], guests=True)
        out = self.go(store, "health", "heart_rate", "anna", "anna", 150, now, crowd)
        self.assertEqual((out[0]["mode"], out[0]["deferred"]), ("diary", True))
        self.assertEqual(json.loads(store.stats())["blocked"], 1)
        back = json.loads(store.tick(ctx(present=["anna"]), now + MIN))
        self.assertEqual(back[0]["mode"], "widget")

    def test_household_is_redacted_for_guests_and_never_leaks(self):
        store = self.make()
        now = DAY + 12 * HOUR
        self.home(store, "anna", now)
        out = self.go(store, "calendar", "event_in_minutes", "anna", "dentist", 10, now + 1, ctx("idle", ["anna"], guests=True, voice=True))
        self.assertTrue(out[0]["redacted"])
        self.assertIsNone(out[0]["action"])
        self.assertEqual(out[0]["mode"], "widget")
        self.assertNotIn("dentist", json.dumps(out))

    def test_critical_bypasses_caps_and_quiet_hours(self):
        store = self.make()
        night = DAY + 2 * HOUR
        out = self.go(store, "security", "intrusion", None, "garage", 1, night, ctx("conversation", voice=True))
        self.assertEqual(out[0]["mode"], "speak")
        self.assertEqual(out[0]["score"], 950)

    def test_hourly_cap(self):
        store = self.make()
        now = DAY + 12 * HOUR
        modes = []
        for i in range(8):
            who = f"p{i}"
            self.home(store, who, now + i)
            out = self.go(store, "calendar", "event_in_minutes", who, f"e{i}", 5, now + i, ctx(present=[who]))
            modes.append("diary" if out[0]["mode"] == "diary" else "shown")
        self.assertEqual(modes.count("shown"), 6)
        self.assertEqual(json.loads(store.stats())["capped"], 2)

    def test_do_and_tell_needs_approval_then_executes_and_can_be_undone(self):
        store = self.make()
        t = DAY + 18 * HOUR
        self.home(store, "anna", t)
        first = self.go(store, "home", "dusk", "anna", "salotto", 1, t + 1)
        self.assertEqual(first[0]["mode"], "widget")
        store.approve_always("evening_lights")
        self.home(store, "anna", t + HOUR)
        second = self.go(store, "home", "dusk", "anna", "cucina", 1, t + HOUR + 1)
        self.assertEqual(second[0]["mode"], "execute")
        self.assertTrue(second[0]["undoable"])
        self.assertEqual(json.loads(store.undoable()), [second[0]["id"]])
        undo = json.loads(store.undo(second[0]["id"], t + HOUR + MIN))
        self.assertEqual((undo["kind"], undo["input_ref"]), ("lights.off", "room:cucina"))
        with self.assertRaises(ValueError):
            store.undo(second[0]["id"], t + HOUR + 2 * MIN)

    def test_two_undos_lower_the_level(self):
        store = self.make()
        t = DAY + 18 * HOUR
        store.approve_always("evening_lights")
        for room in ("a", "b"):
            self.home(store, "anna", t)
            out = self.go(store, "home", "dusk", "anna", room, 1, t + 1)
            self.assertEqual(out[0]["mode"], "execute")
            store.undo(out[0]["id"], t + 2)
            t += 20 * MIN
        self.home(store, "anna", t)
        out = self.go(store, "home", "dusk", "anna", "c", 1, t + 1)
        self.assertEqual(out[0]["mode"], "widget")
        self.assertIn("proactive.why.level_lowered", [r["code"] for r in out[0]["explanation"]["reasons"]])

    def test_approve_always_rules(self):
        store = self.make()
        for rule in ("meeting_soon", "ghost"):
            with self.assertRaises(ValueError):
                store.approve_always(rule)
        store.approve_always("evening_lights")

    def test_feedback_moves_confidence_and_is_per_person(self):
        up, down = self.make(), self.make()
        t = DAY + 8 * HOUR
        for i in range(4):
            for store, verb in ((up, "accept"), (down, "refuse")):
                self.home(store, "anna", t)
                out = self.go(store, "calendar", "event_in_minutes", "anna", f"e{i}", 5, t + 1)
                getattr(store, verb)(out[0]["id"], t + 2)
            t += 2 * HOUR
        for store in (up, down):
            self.home(store, "anna", t)
        hi = self.go(up, "calendar", "event_in_minutes", "anna", "p", 5, t + 1)
        lo = self.go(down, "calendar", "event_in_minutes", "anna", "p", 5, t + 1)
        self.assertGreater(hi[0]["confidence"], 800)
        self.assertLess(lo[0]["confidence"], 800)
        self.home(down, "luca", t)
        other = self.go(down, "calendar", "event_in_minutes", "luca", "p", 5, t + 2, ctx(present=["luca"]))
        self.assertEqual(other[0]["confidence"], 800)

    def test_person_policy_mutes_and_seals(self):
        store = self.make()
        now = DAY + 12 * HOUR
        store.set_policy("anna", json.dumps({"muted": ["calendar"]}))
        self.home(store, "anna", now)
        out = self.go(store, "calendar", "event_in_minutes", "anna", "a", 5, now + 1)
        self.assertEqual((out[0]["mode"], out[0]["deferred"]), ("diary", False))

    def test_forecast_becomes_a_decision(self):
        store = self.make()
        now = DAY + 12 * HOUR
        self.home(store, "anna", now)
        raw = json.dumps({"rule": "meeting_soon", "person": "anna", "subject": "review", "probability": 720})
        out = json.loads(store.forecast(raw, ctx(present=["anna"]), now + 1))
        self.assertEqual((out[0]["explanation"]["origin"], out[0]["confidence"]), ("forecast", 720))
        self.assertEqual(json.loads(store.forecast(raw, ctx(present=["anna"]), now + 2)), [])
        for bad in ({"rule": "ghost", "probability": 5}, {"rule": "meeting_soon", "probability": 5}, {"rule": "meeting_soon", "person": "anna", "probability": 5000}):
            with self.assertRaises(ValueError):
                store.forecast(json.dumps(bad), ctx(), now)

    def test_pending_expires_and_late_accept_fails(self):
        store = self.make()
        now = DAY + 12 * HOUR
        self.home(store, "anna", now)
        out = self.go(store, "calendar", "event_in_minutes", "anna", "a", 5, now + 1)
        store.tick(ctx(present=["anna"]), now + 2 * HOUR)
        self.assertEqual(json.loads(store.pending()), [])
        self.assertEqual(json.loads(store.stats())["expired"], 1)
        with self.assertRaises(ValueError):
            store.accept(out[0]["id"], now + 2 * HOUR)

    def test_notify_has_no_task(self):
        store = self.make()
        now = DAY + 12 * HOUR
        self.go(store, "presence", "home", None, "", 0, now, ctx())
        out = self.go(store, "home", "window_open", None, "kitchen", 1, now + 1, ctx())
        self.assertEqual((out[0]["mode"], out[0]["action"]), ("widget", None))
        with self.assertRaises(ValueError):
            store.accept(out[0]["id"], now + 2)
        store.dismiss(out[0]["id"])

    def test_state_roundtrip_and_tampering(self):
        store = self.make()
        store.approve_always("evening_lights")
        text = store.export_state()
        back = self.make_with(text)
        self.assertEqual(json.loads(back.export_state()), json.loads(text))
        with self.assertRaises(ValueError):
            self.make_with(json.dumps({**json.loads(text), "approved": ["important_email"]}))
        with self.assertRaises(ValueError):
            self.make_with("{")

    def test_hostile_input_is_refused(self):
        store = self.make()
        now = DAY + 12 * HOUR
        good = ctx(present=["anna"])
        for bad in (
            '{"domain":"home","key":"BAD KEY","at":1}',
            '{"domain":"home","key":"k","subject":"a\\nb","at":1}',
            '{"domain":"nowhere","key":"k","at":1}',
            '{"domain":"home","key":"k","at":1,"extra":1}',
            "not json",
        ):
            with self.assertRaises(ValueError):
                store.ingest(bad, good, now)
        with self.assertRaises(ValueError):
            store.ingest(sig("home", "k"), '{"situation":"idle","tz_offset_min":5000}', now)
        with self.assertRaises(ValueError):
            store.ingest(sig("home", "k"), '{"situation":"midnight"}', now)
        for unknown in (9, 10):
            with self.assertRaises(ValueError):
                store.accept(unknown, 0)
            with self.assertRaises(ValueError):
                store.explain(unknown)

    def test_bad_rules_are_refused(self):
        rules = json.loads(proactivity.rules_text())
        kinds = {"door.unlock": "calendar.prepare", "payment.send": "calendar.prepare"}
        for kind in kinds:
            broken = json.loads(json.dumps(rules))
            broken["rules"]["meeting_soon"]["action"]["kind"] = kind
            with self.assertRaises(ValueError):
                self.build(json.dumps(broken))
        broken = json.loads(json.dumps(rules))
        del broken["rules"]["evening_lights"]["action"]["undo"]
        with self.assertRaises(ValueError):
            self.build(json.dumps(broken))
        with self.assertRaises(ValueError):
            self.build("{}")
        with self.assertRaises(ValueError):
            self.build(json.dumps({"rules": rules["rules"], "extra": 1}))


class PythonFallbackTest(Common, unittest.TestCase):
    def make(self):
        return PyProactivity("", proactivity.rules_text())

    def make_with(self, state):
        return PyProactivity("", proactivity.rules_text(), state)

    def build(self, rules):
        return PyProactivity("", rules)


@unittest.skipUnless(NATIVE, "modulo nativo non installato")
class NativeTest(Common, unittest.TestCase):
    def make(self):
        return nuxiva_native.RustProactivity("", proactivity.rules_text())

    def make_with(self, state):
        return nuxiva_native.RustProactivity("", proactivity.rules_text(), state)

    def build(self, rules):
        return nuxiva_native.RustProactivity("", rules)

    def test_habit_predicts_before_the_event(self):
        store = self.make()
        week = 7 * 24 * HOUR
        for w in range(3):
            at = DAY + w * week + 9 * HOUR
            store.ingest(sig("schedule", "wake", "anna", "anna", 1, at), ctx(present=["anna"]), at)
        t = DAY + 3 * week + 8 * HOUR + 50 * MIN
        out = json.loads(store.tick(ctx(present=["anna"]), t))
        self.assertEqual(out[0]["explanation"]["origin"], "habit")
        self.assertEqual(json.loads(store.tick(ctx(present=["anna"]), t + MIN)), [])


class ParityTest(unittest.TestCase):
    @unittest.skipUnless(NATIVE, "modulo nativo non installato")
    def test_same_script_gives_the_same_decisions(self):
        script = []
        t = DAY + 8 * HOUR
        for i in range(10):
            who = f"p{i % 3}"
            script.append(("ingest", sig("presence", "home", who, "", 1, t), ctx(present=[who]), t))
            script.append(("ingest", sig("calendar", "event_in_minutes", who, f"e{i}", 5 + i, t + 1), ctx(present=[who], voice=i % 2 == 0), t + 1))
            script.append(("ingest", sig("health", "heart_rate", who, who, 120 + 5 * i, t + 2), ctx("guests", [who], guests=i % 4 == 0), t + 2))
            script.append(("ingest", sig("email", "important", who, f"m{i}", 700 + 20 * i, t + 3), ctx(present=[who]), t + 3))
            script.append(("tick", ctx(present=[who]), t + 4 * MIN))
            t += 50 * MIN
        for i in range(8):
            who = f"q{i}"
            script.append(("ingest", sig("presence", "home", who, "", 1, t + i), ctx(present=[who]), t + i))
            script.append(("ingest", sig("calendar", "event_in_minutes", who, f"b{i}", 5, t + i), ctx("conversation" if i == 3 else "idle", [who]), t + i))
        night = DAY + 24 * HOUR + 23 * HOUR
        script.append(("ingest", sig("presence", "home", "anna", "", 1, night), ctx(present=["anna"]), night))
        script.append(("ingest", sig("home", "dusk", "anna", "salotto", 1, night + 1), ctx(present=["anna"]), night + 1))
        script.append(("tick", ctx(present=["anna"]), night + 9 * HOUR))
        script.append(("ingest", sig("security", "intrusion", None, "garage", 1, t), ctx("conversation"), t))
        script.append(("tick", ctx(), t + 3 * HOUR))
        runs = []
        for store in (PyProactivity("", proactivity.rules_text()), nuxiva_native.RustProactivity("", proactivity.rules_text())):
            trace = []
            for step in script:
                if step[0] == "ingest":
                    trace.append(json.loads(store.ingest(step[1], step[2], step[3])))
                else:
                    trace.append(json.loads(store.tick(step[1], step[2])))
            for item in json.loads(store.pending())[:3]:
                store.refuse(item["id"], t + 4 * HOUR)
            trace.append(json.loads(store.stats()))
            trace.append(json.loads(store.pending()))
            trace.append(json.loads(store.export_state()))
            runs.append(trace)
        self.assertEqual(runs[0], runs[1])


class GlueTest(unittest.TestCase):
    def test_default_rules_are_valid_in_both_engines(self):
        PyProactivity("", proactivity.rules_text())
        if NATIVE:
            nuxiva_native.RustProactivity("", proactivity.rules_text())

    def test_bridge_translates_bus_events(self):
        proactivity_bridge._state["days"].clear()
        arrived = proactivity_bridge.translate({"name": "person_arrived", "data": {"slug": "anna"}}, 1_000.0, [])
        self.assertEqual(arrived[0], ("presence", "home", "anna", "", 1))
        self.assertEqual(arrived[1][:2], ("schedule", "wake"))
        again = proactivity_bridge.translate({"name": "person_arrived", "data": {"slug": "anna"}}, 2_000.0, [])
        self.assertEqual(len(again), 1)
        left = proactivity_bridge.translate({"name": "person_left", "data": {"slug": "anna"}}, 3.0, [])
        self.assertEqual(left, [("presence", "home", "anna", "", 0)])
        window = proactivity_bridge.translate({"name": "state_changed", "data": {"entity_id": "binary_sensor.window_kitchen", "to": "on"}}, 1.0, [])
        self.assertEqual(window, [("home", "window_open", None, "window_kitchen", 1)])
        dusk = proactivity_bridge.translate({"name": "state_changed", "data": {"entity_id": "sun.sun", "to": "below_horizon", "from": "above_horizon"}}, 1.0, ["anna", "luca"])
        self.assertEqual([d[2] for d in dusk], ["anna", "luca"])
        self.assertEqual(proactivity_bridge.translate({"name": "person_arrived", "data": {"slug": "../x"}}, 1.0, []), [])
        self.assertEqual(proactivity_bridge.translate({"name": "unrelated", "data": {}}, 1.0, []), [])

    def test_snapshot_and_actions_expose_no_subject(self):
        proactivity.reset()
        self.addCleanup(proactivity.reset)
        proactivity._engine["obj"] = proactivity.build(None)
        store = proactivity.get()
        now = proactivity.now_ms()
        store.ingest(sig("presence", "home", "anna", "", 1, now), ctx(present=["anna"]), now)
        store.ingest(sig("health", "heart_rate", "anna", "secret-name", 150, now), '{"situation":"idle","present":["anna"],"tz_offset_min":0}', now)
        items = proactivity.snapshot()["items"]
        for item in items:
            self.assertEqual(set(item), {"id", "summary_key", "rule", "redacted", "undoable", "actionable"})
        self.assertNotIn("secret-name", json.dumps(items))
        self.assertFalse(proactivity.refuse(9999))
        self.assertFalse(proactivity.accept(9999))
        self.assertFalse(proactivity.undo(9999))
        self.assertIsNone(proactivity.explain(9999))


if __name__ == "__main__":
    unittest.main()
