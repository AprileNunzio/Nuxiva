import base64
import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from compute import probe, relay
from compute.relay import ComputeRelay, JobRejected
from permissions.catalog import Level
from permissions.gate import Denied

LINES = [b'{"response":"ci"}\n', b'{"response":"ao"}\n', b'{"done":true}\n']


class FakeOllama(BaseHTTPRequestHandler):
    def log_message(self, *args):
        return

    def do_GET(self):
        routes = {"/api/version": {"version": "0.5.1"}, "/api/tags": {"models": [{"name": "llama3.2:3b", "size": 2 * (1 << 30)}]},
                  "/api/ps": {"models": []}}
        body = json.dumps(routes.get(self.path, {})).encode()
        self.send_response(200 if self.path in routes else 404)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        try:
            for line in LINES:
                self.wfile.write(f"{len(line):x}\r\n".encode() + line + b"\r\n")
                self.wfile.flush()
                time.sleep(0.08)
            self.wfile.write(b"0\r\n\r\n")
        except (BrokenPipeError, ConnectionResetError):
            return


class OllamaCase(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOllama)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        port = self.server.server_address[1]
        for module in (probe, relay):
            patcher = mock.patch.object(module, "PORT", port)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)


class ProbeTest(OllamaCase):
    def test_reports_version_models_and_sizes(self):
        state = probe.OllamaProbe().read()
        self.assertTrue(state["available"])
        self.assertEqual((state["version"], state["models"]), ("0.5.1", [{"name": "llama3.2:3b", "size_gb": 2.0}]))

    def test_unavailable_when_nothing_listens_and_result_is_cached(self):
        self.server.shutdown()
        self.server.server_close()
        instance = probe.OllamaProbe()
        self.assertFalse(instance.read()["available"])
        with mock.patch.object(probe, "_get", side_effect=AssertionError("non va richiamato")):
            self.assertFalse(instance.read()["available"])


class FakeClient:
    def __init__(self, cancel_after: int | None = None):
        self.sent, self.cancel_after = [], cancel_after

    def request(self, path, body, **kwargs):
        self.sent.append((path, body))
        return {"cancel": self.cancel_after is not None and len(self.sent) >= self.cancel_after}


class FakeGate:
    def __init__(self, deny=False):
        self.deny, self.requests = deny, []

    def check(self, request, always_ask=False):
        self.requests.append(request)
        if self.deny:
            raise Denied("no")


class FakePolicy:
    def __init__(self, level=Level.ASK):
        self.value = level

    def level(self, key):
        return self.value


def job(method="POST", path="/api/generate", body=b"{}", job_id="j1") -> dict:
    return {"id": job_id, "method": method, "path": path, "body": base64.b64encode(body).decode()}


def collected(client: FakeClient) -> tuple[bytes, list[dict]]:
    chunks = [b for p, b in client.sent if p == "/api/nodes/compute/chunk"]
    return b"".join(base64.b64decode(c["data"]) for c in chunks), chunks


class RelayTest(OllamaCase):
    def build(self, client=None, gate=None, level=Level.ASK):
        client = client or FakeClient()
        return ComputeRelay(client, gate or FakeGate(), FakePolicy(level), lambda: True), client

    def test_streams_the_whole_answer_with_status_on_the_first_chunk_and_done_on_the_last(self):
        worker, client = self.build()
        worker._execute("j1", job())
        data, chunks = collected(client)
        self.assertEqual(data, b"".join(LINES))
        self.assertEqual((chunks[0]["status"], chunks[0]["content_type"]), (200, "application/x-ndjson"))
        self.assertTrue(chunks[-1]["done"])
        self.assertTrue(all("status" not in c for c in chunks[1:]))

    def test_cancel_from_the_server_stops_reading(self):
        worker, client = self.build(FakeClient(cancel_after=1))
        worker._execute("j1", job())
        self.assertEqual(len(client.sent), 1)

    def test_denied_permission_answers_with_an_error_and_never_calls_ollama(self):
        gate = FakeGate(deny=True)
        worker, client = self.build(gate=gate)
        with mock.patch.object(relay.http.client, "HTTPConnection", side_effect=AssertionError("non va chiamato")):
            worker._execute("j1", job())
        self.assertEqual(client.sent[0][1]["error"], "compute_denied")
        self.assertEqual(gate.requests[0].capability, "compute.ollama")

    def test_dangerous_paths_are_rejected_locally_too(self):
        worker, client = self.build()
        for method, path in (("POST", "/api/pull"), ("POST", "/api/delete"), ("DELETE", "/api/delete"), ("GET", "/api/chat")):
            worker._execute("j1", job(method, path))
        self.assertEqual({b["error"] for _, b in client.sent}, {"compute_path_not_allowed"})
        self.assertEqual(len(client.sent), 4)

    def test_oversized_and_invalid_bodies_are_rejected(self):
        with self.assertRaises(JobRejected) as ctx:
            relay.decode(job(body=b"x" * (relay.BODY_LIMIT + 1)))
        self.assertEqual(ctx.exception.code, "compute_body_too_large")
        broken = job()
        broken["body"] = "@@"
        with self.assertRaises(JobRejected):
            relay.decode(broken)

    def test_unreachable_ollama_is_reported_as_an_error(self):
        self.server.shutdown()
        self.server.server_close()
        worker, client = self.build()
        worker._execute("j1", job())
        self.assertEqual(client.sent[0][1]["error"], "compute_ollama_unreachable")

    def test_sharing_follows_the_permission_and_the_availability(self):
        self.assertTrue(self.build(level=Level.ASK)[0].sharing())
        self.assertFalse(self.build(level=Level.DENY)[0].sharing())
        worker = ComputeRelay(FakeClient(), FakeGate(), FakePolicy(Level.ALLOW), lambda: False)
        self.assertFalse(worker.sharing())


if __name__ == "__main__":
    unittest.main()
