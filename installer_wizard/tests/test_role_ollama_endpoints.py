import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import config
from sealed import SealedFile
from features.brain import api, brains as brains_module, bridge, llm, routing, scope
from features.cloud import catalog, vault as vault_module


class RoleOllamaEndpointTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.env = {"NUXIVA_OLLAMA_URL": "http://legacy.test:11434", "NUXIVA_LLM_ROUTING": "1"}
        self.calls: list[tuple[str, str]] = []
        self.brains = brains_module.Brains()
        self.enterContext(patch.dict(os.environ))
        self.enterContext(patch.dict(catalog.BY_ID))
        self.enterContext(patch.object(vault_module, "_SEALED", SealedFile(self.root / "vault", self.root / "key")))
        self.enterContext(patch.object(vault_module.vault, "_cache", {}))
        self.enterContext(patch.object(api, "write_env", side_effect=self.env.update))
        self.enterContext(patch.object(config, "read_env", return_value=self.env))
        self.enterContext(patch.object(config, "_ollama_cache", {}))
        self.enterContext(patch.object(brains_module, "read_env", return_value=self.env))
        self.enterContext(patch.object(api, "brains", self.brains))
        self.enterContext(patch.object(llm, "brains", self.brains))
        self.enterContext(patch.object(self.brains, "installed", new=AsyncMock(return_value=["local:latest"])))
        self.unload = self.enterContext(patch.object(api, "unload_local_ollama_vram", new_callable=AsyncMock))
        self.free_refs = self.enterContext(patch("features.brain.free_router.failover_engine.configured_refs", new=AsyncMock(return_value=None)))
        self.enterContext(patch.object(llm, "background", side_effect=lambda coroutine: coroutine.close()))
        self.client = httpx.AsyncClient
        self.enterContext(patch("httpx.AsyncClient", side_effect=self.mock_client))

    def mock_client(self, *, timeout: float | httpx.Timeout) -> httpx.AsyncClient:
        return self.client(transport=httpx.MockTransport(self.respond), timeout=timeout)

    def respond(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        model = body["model"]
        self.calls.append((request.url.host, model))
        if request.url.path == "/v1/chat/completions":
            return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})
        return httpx.Response(200, json={"response": "legacy"})

    async def save(self, target: str, model: str, host: str = "", method: str = "ollama_remote") -> dict:
        return await api.single_save_brain_assignment(AsyncMock(json=AsyncMock(return_value={
            "targetId": target, "assignedModel": model, "baseUrl": host, "method": method,
        })))

    async def test_two_roles_keep_distinct_servers_through_routing_and_generation(self) -> None:
        await self.save("reasoning", "remote:8b", "heavy.test")
        await self.save("fast_conversation", "local:latest", method="ollama_local")
        self.assertEqual(self.env["NUXIVA_OLLAMA_URL"], "http://legacy.test:11434")
        deep = self.brains.config()["deep"][0]
        fast = self.brains.config()["chat"][0]
        self.assertNotEqual(deep, fast)
        self.assertTrue(self.brains.usable(deep, {"local:latest"}))
        self.assertEqual(scope.origin(deep), scope.SERVER)
        self.assertEqual(await llm.generate("x", kind="deep", govern=False), "ok")
        self.assertEqual(await llm.generate("x", kind="chat", govern=False), "ok")
        self.assertEqual(self.calls, [("heavy.test", "remote:8b"), ("127.0.0.1", "local:latest")])
        self.unload.assert_not_awaited()

    async def test_repeated_save_reuses_server_and_survives_vault_reload(self) -> None:
        first = await self.save("reasoning", "same:8b", "http://heavy.test:11434/")
        second = await self.save("fast_conversation", "same:8b", "heavy.test")
        self.assertEqual(first["assignedModel"], second["assignedModel"])
        self.assertEqual(len(vault_module.vault.servers()), 1)
        vault_module.vault._cache = None
        self.assertTrue(self.brains.usable(first["assignedModel"], {"other:latest"}))
        self.assertEqual(await llm.generate("x", kind="deep", govern=False), "ok")
        self.assertEqual(self.calls, [("heavy.test", "same:8b")])

    async def test_same_model_name_can_use_different_servers(self) -> None:
        await self.save("reasoning", "same:8b", "heavy.test")
        await self.save("fast_conversation", "same:8b", "light.test")
        await llm.generate("x", kind="deep", govern=False)
        await llm.generate("x", kind="chat", govern=False)
        self.assertEqual(self.calls, [("heavy.test", "same:8b"), ("light.test", "same:8b")])

    async def test_invalid_remote_selection_does_not_change_settings(self) -> None:
        for host in ("", "ftp://heavy.test", "http://user:pass@heavy.test", "heavy.test/path", "heavy.test?x=1"):
            with self.subTest(host=host), self.assertRaises(api.HTTPException):
                await self.save("reasoning", "remote:8b", host)
        self.assertEqual(self.env, {"NUXIVA_OLLAMA_URL": "http://legacy.test:11434", "NUXIVA_LLM_ROUTING": "1"})
        self.assertEqual(vault_module.vault.servers(), {})

    async def test_unqualified_legacy_models_keep_the_global_endpoint(self) -> None:
        self.env.update({"NUXIVA_LLM_DEEP_ORDER": "legacy:latest"})
        self.brains.installed.return_value = ["legacy:latest"]
        self.assertEqual(await llm.generate("x", kind="deep", govern=False), "legacy")
        self.assertEqual(self.calls, [("legacy.test", "legacy:latest")])

    async def test_free_matrix_keeps_bound_ollama_as_a_fallback(self) -> None:
        await self.save("reasoning", "remote:8b", "heavy.test")
        self.free_refs.return_value = []
        self.assertEqual(await llm.generate("x", kind="deep", govern=False), "ok")
        self.assertEqual(self.calls, [("heavy.test", "remote:8b")])

    async def test_failed_remote_falls_back_and_recovers_without_reassignment(self) -> None:
        await self.save("reasoning", "remote:8b", "heavy.test")
        await self.save("fast_conversation", "local:latest", method="ollama_local")
        original = self.respond

        def unavailable(request: httpx.Request) -> httpx.Response:
            if request.url.host == "heavy.test":
                self.calls.append((request.url.host, json.loads(request.content)["model"]))
                return httpx.Response(503)
            return original(request)

        with patch.object(self, "respond", side_effect=unavailable):
            self.assertEqual(await llm.generate("x", kind="deep", govern=False), "ok")
        self.assertEqual(await llm.generate("x", kind="deep", govern=False), "ok")
        self.assertEqual(self.calls, [("heavy.test", "remote:8b"), ("127.0.0.1", "local:latest"),
                                     ("heavy.test", "remote:8b")])

    async def test_later_global_url_change_does_not_retarget_saved_roles(self) -> None:
        await self.save("reasoning", "remote:8b", "heavy.test")
        self.env["NUXIVA_OLLAMA_URL"] = "http://another.test:11434"
        self.assertEqual(await llm.generate("x", kind="deep", govern=False), "ok")
        self.assertEqual(self.calls, [("heavy.test", "remote:8b")])

    async def test_published_core_route_completes_through_the_signed_bridge(self) -> None:
        service = routing.AssignmentService(self.root / "routes")
        with patch.object(routing, "brains", self.brains):
            self.brains.on_change(service.publish)
            saved = await self.save("reasoning", "remote:8b", "heavy.test")
        published = json.loads((self.root / "routes" / "routes.json").read_text(encoding="utf-8"))
        self.assertIn(saved["assignedModel"], published["components"]["analytic_reasoner"])
        self.env["NUXIVA_SECRET_KEY"] = "k" * 64
        body = json.dumps({"ref": saved["assignedModel"], "messages": [{"role": "user", "content": "x"}]}).encode()
        stamp = int(time.time())
        signature = bridge.sign(self.env["NUXIVA_SECRET_KEY"], "POST", bridge.COMPLETE_PATH, stamp, body)

        async def receive() -> dict:
            return {"type": "http.request", "body": body, "more_body": False}

        request = api.Request({"type": "http", "method": "POST", "path": bridge.COMPLETE_PATH,
                               "client": ("127.0.0.1", 1234), "headers": [
                                   (bridge.SIGNATURE_HEADER.lower().encode(), signature.encode()),
                                   (bridge.TIMESTAMP_HEADER.lower().encode(), str(stamp).encode()),
                               ]}, receive)
        with patch("tasks.background", side_effect=lambda coroutine: coroutine.close()):
            result = await bridge.bridge_complete(request)
        self.assertEqual(result["text"], "ok")
        self.assertEqual(self.calls, [("heavy.test", "remote:8b")])

    async def test_failed_vault_save_does_not_reassign_a_role(self) -> None:
        with patch.object(vault_module._SEALED, "save", side_effect=OSError("disk unavailable")):
            with self.assertRaises(OSError):
                await self.save("reasoning", "remote:8b", "heavy.test")
        self.assertNotIn("NUXIVA_LLM_DEEP_ORDER", self.env)
        self.assertEqual(self.env["NUXIVA_OLLAMA_URL"], "http://legacy.test:11434")
        self.assertEqual(vault_module.vault.servers(), {})
        await self.save("reasoning", "remote:8b", "heavy.test")
        vault_module.vault._cache = None
        self.assertEqual(len(vault_module.vault.servers()), 1)
        self.assertEqual(await llm.generate("x", kind="deep", govern=False), "ok")
