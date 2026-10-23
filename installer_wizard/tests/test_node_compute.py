import base64
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from access import require_admin
from features.nodes import compute, compute_routes
from features.nodes import registry as registry_module
from features.nodes.relay import ComputeRelay, RelayError
from features.nodes import relay as relay_module


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


class CleanTest(unittest.TestCase):
    def test_report_is_whitelisted_clamped_and_cleaned(self):
        raw = {"ollama": {"available": 1, "shared": True, "version": "0.5.1<script>", "evil": "x",
                          "models": [{"name": "llama3.2:3b", "size_gb": 2.0}, {"name": "", "size_gb": 1}, "x",
                                     {"name": "m" * 500, "size_gb": 10**9}] + [{"name": "a"}] * 100,
                          "running": "no"}}
        out = compute.clean(raw, registry_module.clean_text)["ollama"]
        self.assertTrue(out["available"] and out["shared"])
        self.assertNotIn("<", out["version"])
        self.assertEqual(len(out["models"]), compute.MODEL_LIMIT - 2)
        self.assertEqual(len(out["models"][1]["name"]), compute.NAME_LIMIT)
        self.assertEqual(out["models"][1]["size_gb"], 4096.0)
        self.assertEqual(out["running"], [])
        self.assertNotIn("evil", out)

    def test_garbage_yields_an_empty_report(self):
        for bad in (None, "x", [], {}, {"ollama": "x"}):
            self.assertEqual(compute.clean(bad, registry_module.clean_text), {})

    def test_ollama_ready_needs_both_availability_and_consent(self):
        self.assertFalse(compute.ollama_ready({}))
        self.assertFalse(compute.ollama_ready({"compute": {"ollama": {"available": True, "shared": False}}}))
        self.assertTrue(compute.ollama_ready({"compute": {"ollama": {"available": True, "shared": True}}}))


class RelayTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.relay = ComputeRelay()

    async def test_streams_chunks_in_order_and_cleans_up(self):
        job = self.relay.submit("pc-a", "POST", "/api/chat", b"{}")
        jobs = await self.relay.take("pc-a", 1)
        self.assertEqual(jobs[0]["id"], job.id)
        self.relay.push("pc-a", {"id": job.id, "data": b64(b"uno\n"), "status": 200, "content_type": "application/x-ndjson"})
        self.relay.push("pc-a", {"id": job.id, "data": b64(b"due\n"), "done": True})
        status, ctype, stream = await self.relay.open(job)
        parts = [part async for part in stream]
        self.assertEqual((status, ctype, parts), (200, "application/x-ndjson", [b"uno\n", b"due\n"]))
        self.assertNotIn(job.id, self.relay.jobs)

    async def test_disallowed_paths_and_oversized_bodies_are_refused(self):
        for method, path in (("POST", "/api/pull"), ("DELETE", "/api/delete"), ("GET", "/api/chat"), ("POST", "/../etc")):
            with self.assertRaises(RelayError) as ctx:
                self.relay.submit("pc-a", method, path, b"")
            self.assertEqual(ctx.exception.status, 403)
        with self.assertRaises(RelayError) as ctx:
            self.relay.submit("pc-a", "POST", "/api/chat", b"x" * (relay_module.MAX_BODY + 1))
        self.assertEqual(ctx.exception.status, 413)

    async def test_a_node_cannot_answer_a_job_of_another_node(self):
        job = self.relay.submit("pc-a", "POST", "/api/chat", b"{}")
        with self.assertRaises(RelayError) as ctx:
            self.relay.push("pc-b", {"id": job.id, "data": ""})
        self.assertEqual(ctx.exception.status, 404)

    async def test_invalid_and_oversized_chunks_are_refused(self):
        job = self.relay.submit("pc-a", "POST", "/api/chat", b"{}")
        with self.assertRaises(RelayError) as ctx:
            self.relay.push("pc-a", {"id": job.id, "data": "@@non-base64@@"})
        self.assertEqual(ctx.exception.code, "compute_invalid_chunk")
        with self.assertRaises(RelayError) as ctx:
            self.relay.push("pc-a", {"id": job.id, "data": b64(b"x" * (relay_module.MAX_CHUNK + 1))})
        self.assertEqual(ctx.exception.status, 413)

    async def test_unpicked_job_times_out_with_a_gateway_error(self):
        job = self.relay.submit("pc-a", "POST", "/api/chat", b"{}")
        with mock.patch.object(relay_module, "PICKUP_TIMEOUT", 0.05):
            with self.assertRaises(RelayError) as ctx:
                await self.relay.open(job)
        self.assertEqual((ctx.exception.status, ctx.exception.code), (504, "compute_node_unreachable"))
        self.assertEqual(await self.relay.take("pc-a", 0.01), [])

    async def test_node_error_before_the_first_byte_is_a_bad_gateway(self):
        job = self.relay.submit("pc-a", "POST", "/api/chat", b"{}")
        await self.relay.take("pc-a", 1)
        self.relay.push("pc-a", {"id": job.id, "error": "compute_ollama_unreachable"})
        with self.assertRaises(RelayError) as ctx:
            await self.relay.open(job)
        self.assertEqual((ctx.exception.status, ctx.exception.code), (502, "compute_ollama_unreachable"))

    async def test_error_in_the_middle_of_a_stream_is_raised_not_swallowed(self):
        job = self.relay.submit("pc-a", "POST", "/api/chat", b"{}")
        await self.relay.take("pc-a", 1)
        self.relay.push("pc-a", {"id": job.id, "data": b64(b"a"), "status": 200})
        self.relay.push("pc-a", {"id": job.id, "error": "compute_denied"})
        _, _, stream = await self.relay.open(job)
        with self.assertRaises(RelayError):
            _ = [part async for part in stream]

    async def test_abandoned_stream_tells_the_node_to_cancel(self):
        job = self.relay.submit("pc-a", "POST", "/api/chat", b"{}")
        await self.relay.take("pc-a", 1)
        self.relay.push("pc-a", {"id": job.id, "data": b64(b"a"), "status": 200})
        _, _, stream = await self.relay.open(job)
        await stream.__anext__()
        await stream.aclose()
        with self.assertRaises(RelayError):
            self.relay.push("pc-a", {"id": job.id, "data": b64(b"b")})

    async def test_queue_is_bounded(self):
        for _ in range(relay_module.MAX_QUEUED):
            self.relay.submit("pc-a", "GET", "/api/tags", b"")
        with self.assertRaises(RelayError) as ctx:
            self.relay.submit("pc-a", "GET", "/api/tags", b"")
        self.assertEqual(ctx.exception.status, 429)


class RouteTest(unittest.TestCase):
    def setUp(self):
        directory = Path(tempfile.mkdtemp())
        patcher = mock.patch.object(registry_module, "NODES_FILE", directory / "nodes.json")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.registry = registry_module.Registry()
        token = self.registry.pair(self.registry.new_code()["code"], "pc-a", {"name": "A", "type": "desktop"})
        self.headers = {"X-Nuxiva-Node": "pc-a", "Authorization": f"Bearer {token}"}
        self.relay = ComputeRelay()
        for target, value in (("registry", self.registry), ("relay", self.relay)):
            patcher = mock.patch.object(compute_routes, target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        app = FastAPI()
        app.include_router(compute_routes.public_routes)
        app.include_router(compute_routes.admin_routes)
        app.dependency_overrides[require_admin] = lambda: "admin"
        self.client = TestClient(app)

    def test_node_endpoints_require_authentication(self):
        self.assertEqual(self.client.post("/api/nodes/compute/next").status_code, 401)
        self.assertEqual(self.client.post("/api/nodes/compute/chunk", json={}).status_code, 401)

    def test_chunk_for_an_unknown_job_is_not_found(self):
        response = self.client.post("/api/nodes/compute/chunk", json={"id": "x"}, headers=self.headers)
        self.assertEqual((response.status_code, response.json()["detail"]), (404, "compute_unknown_job"))

    def test_proxy_requires_a_node_that_shares_ollama(self):
        self.assertEqual(self.client.get("/api/nodes/nessuno/ollama/api/tags").status_code, 404)
        response = self.client.get("/api/nodes/pc-a/ollama/api/tags")
        self.assertEqual((response.status_code, response.json()["detail"]), (409, "compute_ollama_not_shared"))

    def test_proxy_refuses_dangerous_endpoints(self):
        self.registry.data["nodes"]["pc-a"]["compute"] = {"ollama": {"available": True, "shared": True}}
        for path in ("api/pull", "api/delete", "api/create"):
            response = self.client.post(f"/api/nodes/pc-a/ollama/{path}", json={})
            self.assertEqual((response.status_code, response.json()["detail"]), (403, "compute_path_not_allowed"))


if __name__ == "__main__":
    unittest.main()
