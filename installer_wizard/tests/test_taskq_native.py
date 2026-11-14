import json
import os
import tempfile
import threading
import time
import unittest

from agenti.tasks import queue as taskq

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "RustTaskQueue")


def wait(q, task_id, states, timeout=10.0):
    end = time.time() + timeout
    while time.time() < end:
        raw = q.status(task_id)
        if raw and json.loads(raw)["state"] in states:
            return json.loads(raw)
        time.sleep(0.01)
    raise AssertionError(f"{task_id} {q.status(task_id)}")


def handler(spec_json):
    spec = json.loads(spec_json)
    ref = spec["input_ref"]
    if ref == "fail":
        return json.dumps({"error": {"code": "boom", "transient": False}})
    if ref == "garbage":
        return "not json"
    if ref == "block":
        time.sleep(0.3)
    return json.dumps({"evidence": [f"ev:{spec['id']}"]})


class Common:
    def make(self, h=handler):
        raise NotImplementedError

    def setUp(self):
        self.q = self.make()
        self.addCleanup(self.q.shutdown)

    def test_runs_and_reports_evidence(self):
        self.assertEqual(self.q.submit(taskq.spec("a", "job", input_ref="x")), "accepted")
        self.assertEqual(wait(self.q, "a", ("done",))["state"], "done")
        events = json.loads(self.q.events(100))
        self.assertTrue(any(e["id"] == "a" and e["state"] == "done" and e["evidence"] == ["ev:a"] for e in events))

    def test_failure_is_reported_with_code(self):
        self.q.submit(taskq.spec("f", "job", input_ref="fail"))
        found = wait(self.q, "f", ("failed",))
        self.assertEqual(found["error"]["code"], "boom")

    def test_garbage_reply_fails_closed(self):
        self.q.submit(taskq.spec("g", "job", input_ref="garbage"))
        self.assertEqual(wait(self.q, "g", ("failed",))["state"], "failed")

    def test_idempotency_key_dedupes(self):
        self.assertEqual(self.q.submit(taskq.spec("a", "job", idem_key="k", input_ref="block")), "accepted")
        self.assertEqual(self.q.submit(taskq.spec("b", "job", idem_key="k")), "duplicate:a")

    def test_invalid_specs_are_rejected(self):
        with self.assertRaises(ValueError):
            self.q.submit(json.dumps({"id": "a"}))
        with self.assertRaises(ValueError):
            self.q.submit(taskq.spec("Bad Id", "job"))
        with self.assertRaises(ValueError):
            self.q.cancel("ghost")

    def test_cancel_marks_cancelled(self):
        for i in range(8):
            self.q.submit(taskq.spec(f"b{i}", "job", input_ref="block"))
        self.q.submit(taskq.spec("late", "job", input_ref="x"))
        self.q.cancel("late")
        self.assertEqual(json.loads(self.q.status("late"))["state"], "cancelled")
        with self.assertRaises(ValueError):
            self.q.cancel("late")

    def test_stats_shape(self):
        stats = json.loads(self.q.stats())
        for name in taskq.CLASSES:
            self.assertEqual(set(stats[name]), {"queued", "running"})


class PythonFallbackTest(Common, unittest.TestCase):
    def make(self, h=handler):
        return taskq.PyQueue(h)


@unittest.skipUnless(NATIVE, "modulo nativo non installato")
class NativeTest(Common, unittest.TestCase):
    def make(self, h=handler):
        return nuxiva_native.RustTaskQueue("", h, None)

    def test_transient_error_is_retried(self):
        calls = []
        lock = threading.Lock()

        def flaky(spec_json):
            with lock:
                calls.append(1)
                first = len(calls) == 1
            if first:
                return json.dumps({"error": {"code": "net", "transient": True}})
            return json.dumps({"evidence": []})

        settings = json.loads(json.dumps({"voice": self.limits(), "interactive": self.limits(), "background": self.limits(),
                                          "maintenance": self.limits(), "backoff_base_ms": 10, "backoff_cap_ms": 50,
                                          "aging_ms": 1000, "retain_terminal": 100, "event_log": 100}))
        q = nuxiva_native.RustTaskQueue(json.dumps(settings), flaky, None)
        self.addCleanup(q.shutdown)
        q.submit(taskq.spec("a", "job"))
        self.assertEqual(wait(q, "a", ("done",))["attempt"], 2)

    @staticmethod
    def limits():
        return {"capacity": 100, "concurrency": 2, "threads": 1, "ttl_ms": 60000, "max_retries": 2}

    def test_unknown_settings_field_is_rejected(self):
        with self.assertRaises(ValueError):
            nuxiva_native.RustTaskQueue('{"voice": 1}', handler, None)

    def test_wall_budget_enforced(self):
        q = nuxiva_native.RustTaskQueue("", lambda s: (time.sleep(0.5), json.dumps({"evidence": []}))[1], None)
        self.addCleanup(q.shutdown)
        q.submit(taskq.spec("slow", "job", wall_ms=50))
        self.assertEqual(wait(q, "slow", ("failed",))["error"]["code"], "taskq.deadline")

    def test_survives_restart_through_the_journal(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "q.journal")
            gate = threading.Event()
            q1 = nuxiva_native.RustTaskQueue("", lambda s: (gate.wait(5), json.dumps({"evidence": []}))[1], path)
            for i in range(6):
                q1.submit(taskq.spec(f"t{i}", "job", cls="maintenance"))
            time.sleep(0.2)
            q1.shutdown()
            gate.set()
            q2 = nuxiva_native.RustTaskQueue("", handler, path)
            self.addCleanup(q2.shutdown)
            for i in range(6):
                wait(q2, f"t{i}", ("done",))
            self.assertEqual(oct(os.stat(path).st_mode & 0o777), "0o600")

    def test_shutdown_twice_and_use_after_shutdown(self):
        q = self.make()
        q.shutdown()
        with self.assertRaises(RuntimeError):
            q.shutdown()
        with self.assertRaises(ValueError):
            q.submit(taskq.spec("a", "job"))

    def test_tampered_journal_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "q.journal")
            q = nuxiva_native.RustTaskQueue("", handler, path)
            q.submit(taskq.spec("a", "job"))
            wait(q, "a", ("done",))
            q.shutdown()
            with open(path) as fh:
                text = fh.read().replace('"priority":5', '"priority":9', 1)
            with open(path, "w") as fh:
                fh.write(text)
            with self.assertRaises(ValueError):
                nuxiva_native.RustTaskQueue("", handler, path)


class GlueTest(unittest.TestCase):
    def setUp(self):
        taskq.reset()
        self.addCleanup(taskq.reset)
        taskq._handlers.clear()
        taskq._kinds.clear()
        taskq._live.clear()

    def test_dispatch_maps_handlers_and_errors(self):
        taskq.register("ok", lambda ref, scope: [ref])
        taskq.register("bad", lambda ref, scope: 1 / 0 if False else (_ for _ in ()).throw(ValueError("x")))
        taskq.register("retry", lambda ref, scope: (_ for _ in ()).throw(taskq.TransientError("net")))
        self.assertEqual(json.loads(taskq.dispatch(taskq.spec("a", "ok", input_ref="r"))), {"evidence": ["r"]})
        self.assertEqual(json.loads(taskq.dispatch(taskq.spec("b", "bad")))["error"], {"code": "task.failed", "transient": False})
        self.assertTrue(json.loads(taskq.dispatch(taskq.spec("c", "retry")))["error"]["transient"])
        self.assertEqual(json.loads(taskq.dispatch(taskq.spec("d", "nope")))["error"]["code"], "task.no_handler")
        self.assertEqual(json.loads(taskq.dispatch("not json"))["error"]["code"], "task.failed")

    def test_snapshot_reports_phrases_data_only(self):
        q = taskq.build(handler)
        taskq._queue["obj"] = q
        taskq.enqueue("job1", "build", input_ref="x")
        wait(q, "job1", ("done",))
        snap = taskq.snapshot()
        self.assertEqual(snap["items"][0]["kind"], "build")
        self.assertEqual(snap["active"], 0)
        self.assertNotIn("x", json.dumps(snap["items"]))


if __name__ == "__main__":
    unittest.main()
