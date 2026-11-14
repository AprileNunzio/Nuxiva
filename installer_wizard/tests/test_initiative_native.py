import json
import unittest

from agenti.autonomy import initiative

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "RustInitiative")
HOUR = 3_600_000


class Common:
    def make(self):
        raise NotImplementedError

    def see(self, store, subject, situation="idle", voice=False, now=0):
        return json.loads(store.observe(initiative.event("fs", "modified", subject, now), situation, voice, now))

    def test_edit_becomes_a_widget_proposal_with_a_valid_task(self):
        store = self.make()
        out = self.see(store, "project:site")
        self.assertEqual(out[0]["mode"], "widget")
        self.assertEqual(out[0]["action"]["input_ref"], "project:site")
        self.assertEqual(out[0]["action"]["kind"], "dev_check")
        self.assertEqual(len(json.loads(store.pending())), 1)

    def test_unrelated_subject_is_ignored(self):
        self.assertEqual(self.see(self.make(), "docs:readme"), [])

    def test_nothing_surfaces_during_a_conversation(self):
        store = self.make()
        out = self.see(store, "project:site", situation="conversation", voice=True)
        self.assertEqual(out[0]["mode"], "diary")
        self.assertEqual(json.loads(store.pending()), [])

    def test_duplicates_are_suppressed(self):
        store = self.make()
        self.assertEqual(len(self.see(store, "project:site", now=0)), 1)
        self.assertEqual(self.see(store, "project:site", now=10), [])

    def test_accept_returns_the_task_once(self):
        store = self.make()
        pid = self.see(store, "project:site")[0]["id"]
        action = json.loads(store.accept(pid, 1))
        self.assertEqual(action["kind"], "dev_check")
        with self.assertRaises(ValueError):
            store.accept(pid, 2)

    def test_refusal_is_remembered_and_counted(self):
        store = self.make()
        pid = self.see(store, "project:a")[0]["id"]
        store.refuse(pid, 1)
        stats = json.loads(store.stats())
        self.assertEqual((stats["refused"], stats["accepted"]), (1, 0))

    def test_hostile_input_is_refused(self):
        store = self.make()
        with self.assertRaises(ValueError):
            store.observe("not json", "idle", False, 0)
        with self.assertRaises(ValueError):
            store.observe(initiative.event("fs", "modified", "project:x"), "midnight", False, 0)

    def test_no_approve_always_for_unknown(self):
        with self.assertRaises(ValueError):
            self.make().approve_always("ghost")


class PythonFallbackTest(Common, unittest.TestCase):
    def make(self):
        return initiative.PyInitiative("", initiative.catalog_text())


@unittest.skipUnless(NATIVE, "modulo nativo non installato")
class NativeTest(Common, unittest.TestCase):
    def make(self):
        return nuxiva_native.RustInitiative("", initiative.catalog_text())

    def test_hourly_cap(self):
        store = self.make()
        modes = [self.see(store, f"project:p{i}", now=i)[0]["mode"] for i in range(9)]
        self.assertEqual(sum(m != "diary" for m in modes), 6)
        self.assertEqual(self.see(store, "project:late", now=HOUR + 100)[0]["mode"], "widget")

    def test_deferred_idea_is_released_after_the_conversation(self):
        store = self.make()
        self.see(store, "project:site", situation="conversation")
        self.assertEqual(json.loads(store.tick("conversation", False, 1_000)), [])
        released = json.loads(store.tick("idle", False, 2_000))
        self.assertEqual(released[0]["mode"], "widget")

    def test_voice_only_when_free_and_idle(self):
        store = self.make()
        self.assertEqual(self.see(store, "project:a", voice=True)[0]["mode"], "speak")
        self.assertEqual(self.see(store, "project:b", situation="guests", voice=True, now=5)[0]["mode"], "widget")

    def test_state_roundtrip_and_tampered_state(self):
        store = self.make()
        store.approve_always("project-edit")
        text = store.export_state()
        back = nuxiva_native.RustInitiative("", initiative.catalog_text(), text)
        self.assertEqual(back.export_state(), text)
        with self.assertRaises(ValueError):
            nuxiva_native.RustInitiative("", initiative.catalog_text(), text.replace("project-edit", "ghost"))

    def test_bad_catalog_and_settings_are_refused(self):
        with self.assertRaises(ValueError):
            nuxiva_native.RustInitiative("", "{}")
        with self.assertRaises(ValueError):
            nuxiva_native.RustInitiative('{"x": 1}', initiative.catalog_text())


class GlueTest(unittest.TestCase):
    def test_snapshot_exposes_only_keys_and_ids(self):
        initiative.reset()
        self.addCleanup(initiative.reset)
        initiative._engine["obj"] = initiative.build(None)
        store = initiative.get()
        store.observe(initiative.event("fs", "modified", "project:secret-name"), "idle", False, initiative.now_ms())
        items = initiative.snapshot()["items"]
        self.assertEqual(set(items[0]), {"id", "summary_key", "observer"})
        self.assertNotIn("secret-name", json.dumps(items))
        self.assertFalse(initiative.refuse(9999))


if __name__ == "__main__":
    unittest.main()
