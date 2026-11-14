import json
import unittest

from agenti.mind import reflect

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "RustReflect")
DAY = 86_400_000


class Common:
    def make(self, snapshot=None):
        raise NotImplementedError

    def propose(self, store, kind, value, now=0, task="t"):
        raw = store.record(reflect.reflection(task, "success", proposed=(kind, value)), now)
        return json.loads(raw)["candidate"]

    def test_user_confirm_adopts_and_revert_restores(self):
        s = self.make()
        a = self.propose(s, "reply_tone", "warm", task="a")
        s.confirm(a, 1)
        self.assertEqual(json.loads(s.lesson_for("reply_tone"))["value"], "warm")
        b = self.propose(s, "reply_tone", "formal", 2, task="b")
        s.confirm(b, 3)
        self.assertEqual(json.loads(s.lesson_for("reply_tone"))["value"], "formal")
        s.revert("reply_tone", 4)
        if NATIVE and isinstance(s, nuxiva_native.RustReflect):
            self.assertEqual(json.loads(s.lesson_for("reply_tone"))["value"], "warm")
        else:
            self.assertIsNone(s.lesson_for("reply_tone"))

    def test_reject_forgets_and_blocks(self):
        s = self.make()
        a = self.propose(s, "reply_tone", "warm")
        s.confirm(a, 1)
        s.reject(a, 2)
        self.assertIsNone(s.lesson_for("reply_tone"))
        again = json.loads(s.record(reflect.reflection("x", "success", proposed=("reply_tone", "warm")), 3))
        self.assertTrue(again["blocked"])
        with self.assertRaises(ValueError):
            s.reject(a, 4)

    def test_catalog_is_enforced(self):
        s = self.make()
        with self.assertRaises(ValueError):
            s.record(reflect.reflection("x", "success", observed=[("ghost", "a")]), 0)
        with self.assertRaises(ValueError):
            s.record(reflect.reflection("x", "success", proposed=("reply_tone", "angry")), 0)
        with self.assertRaises(ValueError):
            s.confirm(999, 0)

    def test_code_proposals_are_only_queued(self):
        s = self.make()
        body = json.loads(reflect.reflection("x", "failure"))
        body["proposed"] = {"type": "code", "request_ref": "fix-login"}
        out = json.loads(s.record(json.dumps(body), 0))
        self.assertEqual(out["code_request"], "fix-login")
        self.assertEqual(json.loads(s.lessons("adopted")), [])
        self.assertEqual(json.loads(s.take_code_requests()), ["fix-login"])

    def test_export_roundtrip(self):
        s = self.make()
        a = self.propose(s, "reply_length", "short")
        s.confirm(a, 1)
        back = self.make(s.export())
        self.assertEqual(json.loads(back.lesson_for("reply_length"))["value"], "short")

    def test_unknown_state_is_refused(self):
        with self.assertRaises(ValueError):
            self.make().lessons("bogus")


class PythonFallbackTest(Common, unittest.TestCase):
    def make(self, snapshot=None):
        return reflect.PyReflect("", reflect.catalog_text(), snapshot)


@unittest.skipUnless(NATIVE, "modulo nativo non installato")
class NativeTest(Common, unittest.TestCase):
    def make(self, snapshot=None):
        return nuxiva_native.RustReflect("", reflect.catalog_text(), snapshot)

    def feed(self, s, kind, value, outcome, attempts, n, prefix, now=0):
        for i in range(n):
            s.record(reflect.reflection(f"{prefix}{i}", outcome, attempts=attempts, observed=[(kind, value)]), now)

    def test_verified_lesson_is_adopted_automatically(self):
        s = self.make()
        self.feed(s, "reminder_time", "morning", "failure", 2, 5, "m")
        self.feed(s, "reminder_time", "evening", "success", 1, 5, "e")
        s.record(reflect.reflection("c", "success", observed=[("reminder_time", "evening")], proposed=("reminder_time", "evening")), 0)
        self.assertEqual(json.loads(s.lesson_for("reminder_time"))["value"], "evening")

    def test_unverified_lesson_stays_a_candidate(self):
        s = self.make()
        s.record(reflect.reflection("c", "success", proposed=("reminder_time", "evening")), 0)
        self.assertIsNone(s.lesson_for("reminder_time"))
        self.assertEqual(len(json.loads(s.lessons("candidate"))), 1)

    def test_candidate_expires(self):
        s = self.make()
        s.record(reflect.reflection("c", "success", proposed=("reminder_time", "evening")), 0)
        s.maintain(15 * DAY)
        self.assertEqual(json.loads(s.lessons("candidate")), [])

    def test_hostile_inputs_are_refused(self):
        s = self.make()
        for bad in ("nope", "{}", json.dumps({"schema_version": 1, "task": "x", "outcome": "success", "extra": 1})):
            with self.assertRaises(ValueError):
                s.record(bad, 0)
        with self.assertRaises(ValueError):
            nuxiva_native.RustReflect("", "{}", None)
        with self.assertRaises(ValueError):
            nuxiva_native.RustReflect("", reflect.catalog_text(), '{"schema_version": 1}')


class GlueTest(unittest.TestCase):
    def test_snapshot_lists_only_phrase_data(self):
        reflect.reset()
        self.addCleanup(reflect.reset)
        reflect._store["obj"] = reflect.build(None)
        store = reflect.get()
        lid = json.loads(store.record(reflect.reflection("t", "success", proposed=("reply_tone", "warm")), reflect.now_ms()))["candidate"]
        data = reflect.snapshot()
        self.assertEqual(data["items"], [{"id": lid, "kind": "reply_tone", "value": "warm", "state": "candidate"}])
        self.assertFalse(reflect.keep(9999))


if __name__ == "__main__":
    unittest.main()
