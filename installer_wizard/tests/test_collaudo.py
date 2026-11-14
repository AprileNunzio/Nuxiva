import asyncio
import json
import socket
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

for p in (str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[1] / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

import native_core
from agenti.collaudo import emit, hub, intake, paths, pyhub, tokens

NATIVE = native_core.load()
READY = NATIVE is not None and hasattr(NATIVE, "RustCollaudo")
KEY = "07" * 32
LEAKS = ("Mario", "Rossi", "noci", "example.com", "3331234567")
RAW = {"domain": "ear", "level": "info", "kind": "verdict", "src": "test", "corr": "abcdef0123456789", "at_ms": 1700000000000,
       "fields": {"speaker_name": "Mario Rossi", "transcript": "ho allergia alle noci", "contact": "mario.rossi@example.com",
                  "phone_note": "3331234567", "zone": "kitchen", "frames": 3, "ok": True, "latency_ms": 12.5, "spk_ref": "mario"}}


def isolated(test: unittest.TestCase) -> Path:
    root = Path(tempfile.mkdtemp())
    for name, value in (("ROOT", root), ("LOG_DIR", root / "log"), ("PY_LOG_DIR", root / "log_py"), ("KEY_FILE", root / "key"),
                        ("TOKEN_FILE", root / "token"), ("MODE_FILE", root / "mode"), ("SOCKET", root / "i.sock"),
                        ("BASELINE", root / "baseline.json")):
        patcher = mock.patch.object(paths, name, value)
        patcher.start()
        test.addCleanup(patcher.stop)
    hub.reset()
    test.addCleanup(hub.reset)
    test.addCleanup(emit.bind_local, None)
    return root


def without_native(test: unittest.TestCase) -> None:
    patcher = mock.patch.object(native_core, "symbol", return_value=None)
    patcher.start()
    test.addCleanup(patcher.stop)


class FallbackTest(unittest.TestCase):

    def setUp(self):
        isolated(self)
        without_native(self)

    def test_redacts_and_stores(self):
        h = hub.get()
        self.assertIsInstance(h, pyhub.PyHub)
        self.assertEqual(hub.emit(RAW), 1)
        text = json.dumps(hub.query({}))
        for leak in LEAKS:
            self.assertNotIn(leak, text)
        fields = hub.query({})[0]["fields"]
        self.assertEqual(fields["zone"], "kitchen")
        self.assertTrue(fields["spk_ref"].startswith("h:"))
        self.assertGreater(fields["redacted_n"], 3)

    def test_verbose_needs_collaudo_mode(self):
        self.assertIsNone(hub.emit({**RAW, "level": "trace"}))
        hub.set_mode(True)
        self.assertEqual(hub.emit({**RAW, "level": "trace"}), 1)

    def test_invalid_input_is_refused(self):
        for bad in ({**RAW, "kind": "Bad Kind"}, {**RAW, "corr": "zz"}, {**RAW, "domain": "nope"}, {**RAW, "extra": 1}):
            with self.assertRaises(ValueError):
                hub.emit(bad)

    def test_report_requires_native(self):
        hub.emit(RAW)
        with self.assertRaises(RuntimeError):
            hub.report({})

    def test_token_roundtrip(self):
        token = tokens.issue()
        self.assertTrue(tokens.verify(token))
        self.assertFalse(tokens.verify("0" * 64))
        self.assertNotIn(token, paths.TOKEN_FILE.read_text())
        tokens.revoke()
        self.assertFalse(tokens.verify(token))


@unittest.skipUnless(READY, "modulo nativo collaudo-core non installato")
class NativeTest(unittest.TestCase):

    def setUp(self):
        isolated(self)

    def test_chain_and_report(self):
        self.assertTrue(hub.native())
        hub.emit(RAW)
        hub.emit({"domain": "probe", "level": "info", "kind": "bus_roundtrip", "src": "t", "fields": {"outcome": "ok", "latency_ms": 3}})
        self.assertTrue(json.loads(hub.get().verify())["ok"])
        report = hub.report({})
        self.assertEqual(report["events"], 2)
        status = {c["id"]: c["status"] for c in report["checks"]}
        self.assertEqual(status["bus_roundtrip"], "pass")
        self.assertEqual(status["camera_frame"], "missing")

    def test_token_native(self):
        token = tokens.issue()
        self.assertTrue(tokens.verify(token))
        self.assertFalse(tokens.verify("f" * 64))
        self.assertFalse(tokens.verify("short"))

    def test_python_and_rust_redact_alike(self):
        cases = ["failed for /home/mario/docs mail a.b@c.it id 12345678901 ok", "plain text here", "token " + "a" * 40,
                 "call +39 333 123 4567 now", "abc 1234567 def", "x" * 200]
        for case in cases:
            self.assertEqual(NATIVE.collaudo_scrub_text(case), pyhub.scrub_text(case), case)

    def test_python_and_rust_fields_match(self):
        rust = hub.get()
        rust.emit(json.dumps({**RAW, "domain": "error", "level": "error", "fields": {**RAW["fields"], "msg": "boom for /home/ann/x 99999999"}}))
        rows = json.loads(rust.query("{}"))
        py = pyhub.PyHub(Path(tempfile.mkdtemp()), KEY, 1 << 20, 4)
        py.emit(json.dumps({**RAW, "domain": "error", "level": "error", "fields": {**RAW["fields"], "msg": "boom for /home/ann/x 99999999"}}))
        mirrored = json.loads(py.query("{}"))
        keys = lambda row: {k: v for k, v in row["fields"].items() if not (isinstance(v, str) and v.startswith("h:"))}
        self.assertEqual(keys(rows[0]), keys(mirrored[0]))
        self.assertEqual(set(rows[0]["fields"]), set(mirrored[0]["fields"]))


class IntakeTest(unittest.IsolatedAsyncioTestCase):

    async def test_datagram_reaches_hub(self):
        isolated(self)
        without_native(self)
        transport = await intake.serve()
        self.addCleanup(transport.close)
        self.assertEqual(oct(paths.SOCKET.stat().st_mode & 0o777), "0o600")
        client = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.addCleanup(client.close)
        client.sendto(json.dumps({"domain": "vision", "level": "warn", "kind": "slow", "src": "vision", "fields": {"fps": 4}}).encode(), str(paths.SOCKET))
        client.sendto(b"garbage", str(paths.SOCKET))
        for _ in range(50):
            await asyncio.sleep(0.02)
            if hub.query({}):
                break
        rows = hub.query({})
        self.assertEqual([r["kind"] for r in rows], ["slow"])

    async def test_emit_never_raises_and_correlates(self):
        isolated(self)
        without_native(self)
        self.assertFalse(emit.emit("ear", "info", "x"))
        emit.bind_local(lambda raw: hub.emit(raw))
        with emit.correlation("aaaaaaaaaaaaaaaa"):
            self.assertTrue(emit.emit("ear", "info", "heard", n=1))
        self.assertEqual(hub.query({})[0]["corr"], "aaaaaaaaaaaaaaaa")
        self.assertTrue(emit.emit("ear", "bogus", "heard") in (True, False))


class ApiTest(unittest.TestCase):

    def setUp(self):
        isolated(self)
        try:
            from fastapi import FastAPI
            from fastapi.testclient import TestClient
            from agenti.collaudo import api
        except ImportError as exc:
            self.skipTest(str(exc))
        app = FastAPI()
        app.include_router(api.admin_routes)
        self.client = TestClient(app)
        patcher = mock.patch.object(api, "peer", return_value="127.0.0.1")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.api = api
        self.token = tokens.issue()
        self.auth = {"Authorization": f"Bearer {self.token}"}
        now = {"at_ms": int(time.time() * 1000)}
        hub.emit({**RAW, **now})
        hub.emit({**RAW, **now, "domain": "error", "level": "error", "kind": "boom", "fields": {"msg": "failed for /home/x/y"}})

    def test_disarmed_is_invisible(self):
        tokens.revoke()
        self.assertEqual(self.client.get("/api/collaudo/status", headers=self.auth).status_code, 404)

    def test_requires_token_and_loopback(self):
        self.assertEqual(self.client.get("/api/collaudo/status").status_code, 401)
        self.assertEqual(self.client.get("/api/collaudo/status", headers={"Authorization": "Bearer " + "0" * 64}).status_code, 401)
        with mock.patch.object(self.api, "peer", return_value="10.0.0.5"):
            self.assertEqual(self.client.get("/api/collaudo/status", headers=self.auth).status_code, 403)
        self.assertEqual(self.client.get("/api/collaudo/status", headers=self.auth).status_code, 200)

    def test_brute_force_is_throttled(self):
        for _ in range(tokens.LIMIT):
            self.client.get("/api/collaudo/status", headers={"Authorization": "Bearer " + "1" * 64})
        self.assertEqual(self.client.get("/api/collaudo/status", headers=self.auth).status_code, 429)
        tokens._failures.clear()

    def test_events_filter_and_cursor(self):
        body = self.client.get("/api/collaudo/events?min_level=error", headers=self.auth).json()
        self.assertEqual([e["kind"] for e in body["events"]], ["boom"])
        later = self.client.get(f"/api/collaudo/events?since_seq={body['last_seq']}", headers=self.auth).json()
        self.assertEqual(later["events"], [])
        self.assertEqual(self.client.get("/api/collaudo/events?domain=bogus", headers=self.auth).status_code, 422)

    def test_post_needs_header_and_validates(self):
        self.assertEqual(self.client.post("/api/collaudo/mode", json={"enabled": True}, headers=self.auth).status_code, 403)
        headers = {**self.auth, "X-Nuxiva-Request": "1"}
        self.assertEqual(self.client.post("/api/collaudo/mode", json={"enabled": True}, headers=headers).status_code, 200)
        self.assertEqual(self.client.post("/api/collaudo/mode", json={"enabled": True, "x": 1}, headers=headers).status_code, 422)
        self.assertEqual(self.client.post("/api/collaudo/mark", json={"label": "Bad Label"}, headers=headers).status_code, 422)
        self.assertEqual(self.client.post("/api/collaudo/mark", json={"label": "start_test"}, headers=headers).status_code, 200)
        self.assertEqual(self.client.post("/api/collaudo/smoke", json={"only": ["nope"]}, headers=headers).status_code, 422)

    @unittest.skipUnless(READY, "modulo nativo collaudo-core non installato")
    def test_report_and_verify(self):
        report = self.client.get("/api/collaudo/report?lang=it", headers=self.auth).json()
        self.assertEqual(report["report"]["verdict"], "fail")
        self.assertIn("services", report["hints"])
        self.assertTrue(self.client.get("/api/collaudo/verify", headers=self.auth).json()["ok"])
        headers = {**self.auth, "X-Nuxiva-Request": "1"}
        self.assertTrue(self.client.post("/api/collaudo/baseline", headers=headers).json()["saved"])
        self.assertEqual(oct(paths.BASELINE.stat().st_mode & 0o777), "0o600")


class SmokeTest(unittest.IsolatedAsyncioTestCase):

    @unittest.skipUnless(READY, "modulo nativo collaudo-core non installato")
    async def test_smoke_runs_without_hardware(self):
        isolated(self)
        from agenti.collaudo import smoke
        emit.bind_local(lambda raw: hub.emit(raw))
        result = await smoke.run(["bus_roundtrip", "camera_frame", "services"])
        outcomes = {r["kind"]: r["outcome"] for r in result["results"]}
        self.assertEqual(outcomes["bus_roundtrip"], "ok")
        self.assertIn(outcomes["camera_frame"], ("skip", "fail"))
        self.assertEqual(result["report"]["checks"][1]["id"], "bus_roundtrip")
        self.assertFalse(hub.get().collaudo())

    async def test_scenario_validates_and_skips_without_programme(self):
        isolated(self)
        without_native(self)
        from agenti.collaudo import smoke
        emit.bind_local(lambda raw: hub.emit(raw))
        with self.assertRaises(ValueError):
            await smoke.scenario("nope", 5)
        with mock.patch.object(asyncio, "sleep", new=mock.AsyncMock()):
            result = await smoke.scenario("radio_rejected", 3)
        self.assertEqual(result["outcome"], "skip")


class EarTapTest(unittest.TestCase):

    def test_tap_sends_only_safe_fields(self):
        ear = Path(__file__).resolve().parents[1] / "agenti/percezione/ear"
        sys.path.insert(0, str(ear))
        self.addCleanup(sys.path.remove, str(ear))
        sys.modules.pop("collaudo_tap", None)
        import collaudo_tap

        sent = []
        with mock.patch.object(collaudo_tap, "_send", sent.append):
            origin = mock.Mock()
            origin._programme.return_value = True
            collaudo_tap.observe(origin, {"type": "transcript", "text": "ho allergia alle noci", "speaker": "mario", "ms": 400,
                                          "voice_known": True, "lang": "it"})
        text = json.dumps(sent)
        self.assertNotIn("noci", text)
        self.assertNotIn('"speaker"', text)
        self.assertEqual(sent[0]["fields"]["spk_ref"], "mario")
        self.assertTrue(sent[0]["fields"]["programme"])
        self.assertEqual(sent[0]["kind"], "transcript")


if __name__ == "__main__":
    unittest.main()
