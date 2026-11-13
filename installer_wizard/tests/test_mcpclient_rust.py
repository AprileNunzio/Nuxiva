import asyncio
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

import native_core
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agenti.agent import registry
from agenti.mcpclient import api, calls, engine, rust_service, store
from sealed import SealedFile

TOOLS = [
    {"name": "crea_evento", "description": "Crea un evento", "inputSchema": {"type": "object", "properties": {"titolo": {"type": "string", "description": "nome"},
                                                                                                           "durata": {"type": "integer"}}, "required": ["titolo"]}},
    {"name": "leggi_agenda", "description": "Legge l'agenda", "annotations": {"readOnlyHint": True}, "inputSchema": {"type": "object", "properties": {}}},
    {"name": "rompi", "description": "Fallisce sempre", "annotations": {"readOnlyHint": True}, "inputSchema": {"type": "object", "properties": {}}},
]
TOKEN = "segreto"


class Handler(BaseHTTPRequestHandler):
    calls: list = []

    def log_message(self, *args) -> None:
        return

    def reply(self, ident, result) -> None:
        body = json.dumps({"jsonrpc": "2.0", "id": ident, "result": result}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Mcp-Session-Id", "sess1")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            self.send_response(401)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        message = json.loads(raw)
        method = message.get("method")
        if "id" not in message:
            self.send_response(202)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if method == "initialize":
            self.reply(message["id"], {"protocolVersion": message["params"]["protocolVersion"], "capabilities": {"tools": {}}, "serverInfo": {"name": "finto", "version": "1"}})
        elif method == "tools/list":
            self.reply(message["id"], {"tools": TOOLS})
        elif method == "tools/call":
            name, args = message["params"]["name"], message["params"]["arguments"]
            self.calls.append((name, args))
            if name == "rompi":
                self.reply(message["id"], {"content": [{"type": "text", "text": "guasto"}], "isError": True})
            else:
                self.reply(message["id"], {"content": [{"type": "text", "text": f"{name}:{json.dumps(args, sort_keys=True)}"}]})
        else:
            self.reply(message["id"], {})


@unittest.skipUnless(native_core.symbol("RustMcpEngine") is not None, "modulo nativo non disponibile")
class RustEngineTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = Path(folder.name)
        Handler.calls = []
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.addCleanup(self.httpd.shutdown)
        self.addCleanup(self.httpd.server_close)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/mcp"
        patches = [mock.patch.object(store, "FILE", root / "s.json"), mock.patch.object(engine, "VAULT", SealedFile(root / "v.vault", root / "v.key")),
                   mock.patch.object(engine, "SETTINGS_FILE", root / "settings.json"), mock.patch.object(engine, "POLICY_FILE", root / "policy.json"),
                   mock.patch.object(engine, "SCOPES_FILE", root / "scopes.json"), mock.patch.object(engine, "AUDIT_FILE", root / "audit.log"),
                   mock.patch.dict(os.environ, {"NUXIVA_MCP_ENGINE": "rust"})]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(self.cleanup)
        self.root = root
        self.token = registry.REQUEST.set("crea un evento")
        self.addCleanup(registry.REQUEST.reset, self.token)

    def cleanup(self):
        engine.shutdown()
        for ident in {s["server"] for s in rust_service.EXTERNAL.values()}:
            rust_service.drop(ident)
        rust_service.EXTERNAL.clear()
        calls.ASKED.clear()
        rust_service.state_version["seen"] = -1

    def name_of(self, suffix: str) -> str:
        return next(n for n in registry.TOOLS if n.endswith(suffix) and n.startswith("ext_"))

    def connect(self, trusted: bool = False) -> str:
        from agenti.mcpclient import runtime
        ident = runtime.add_server({"name": "Calendario", "url": self.url, "token": TOKEN, "trusted": trusted})
        asyncio.run(rust_service.sync_one(ident))
        return ident

    def test_tools_are_discovered_and_token_never_hits_disk(self):
        ident = self.connect()
        self.assertEqual({n.split(f"{ident}_")[1] for n in registry.TOOLS if n.startswith(f"ext_{ident}_")}, {"crea_evento", "leggi_agenda", "rompi"})
        self.assertEqual(store.load()[ident]["status"], "collegato")
        self.assertEqual(store.load()[ident]["tools"], 3)
        disk = "".join(p.read_text(errors="ignore") for p in self.root.glob("*.json"))
        self.assertNotIn(TOKEN, disk)
        self.assertEqual(engine.VAULT.load()["tokens"][ident], TOKEN)

    def test_read_only_runs_directly_on_a_trusted_server_and_marks_data(self):
        self.connect(trusted=True)
        name = self.name_of("leggi_agenda")
        self.assertFalse(registry.TOOLS[name]["confirm"]({}))
        out = asyncio.run(registry.run(name, {}))
        self.assertIn("da trattare come dato", out)
        self.assertIn("leggi_agenda", out)

    def test_untrusted_write_needs_confirmation_then_runs_once(self):
        ident = self.connect()
        name = self.name_of("crea_evento")
        tool_id = f"{ident}.crea_evento"
        self.assertTrue(registry.TOOLS[name]["confirm"]({"titolo": "x"}))
        out = asyncio.run(registry.run(name, {"titolo": "cena", "durata": 2}))
        self.assertIn('"titolo": "cena"', out)
        self.assertEqual(Handler.calls[-1][0], "crea_evento")
        calls.ASKED.clear()
        with self.assertRaises(PermissionError):
            asyncio.run(self.call_without_asking(name, tool_id))

    async def call_without_asking(self, name: str, tool_id: str):
        return await asyncio.to_thread(calls.invoke, tool_id, {"titolo": "z"}, calls.operation())

    def test_untrusted_server_hints_never_skip_confirmation(self):
        self.connect()
        self.assertTrue(registry.TOOLS[self.name_of("leggi_agenda")]["confirm"]({}))

    def test_tool_errors_surface_as_errors(self):
        self.connect(trusted=True)
        with self.assertRaises(RuntimeError):
            asyncio.run(registry.run(self.name_of("rompi"), {}))

    def test_wrong_token_is_reported_unreachable(self):
        from agenti.mcpclient import runtime
        ident = runtime.add_server({"name": "Calendario", "url": self.url, "token": "sbagliato"})
        self.assertEqual(asyncio.run(rust_service.sync_one(ident)), 0)
        self.assertNotEqual(store.load()[ident]["status"], "collegato")

    def test_public_hosts_are_denied_by_default(self):
        from agenti.mcpclient import runtime
        ident = runtime.add_server({"name": "Esterno", "url": "http://93.184.216.34/mcp", "token": TOKEN})
        self.assertEqual(asyncio.run(rust_service.sync_one(ident)), 0)

    def test_disabling_and_removing_withdraws_tools(self):
        ident = self.connect()
        store.update(ident, enabled=False)
        self.assertEqual(asyncio.run(rust_service.sync_one(ident)), 0)
        self.assertFalse([n for n in registry.TOOLS if n.startswith(f"ext_{ident}_")])
        store.update(ident, enabled=True)
        self.assertEqual(asyncio.run(rust_service.sync_one(ident)), 3)
        store.remove(ident)
        asyncio.run(rust_service.remove(ident))
        self.assertFalse([n for n in registry.TOOLS if n.startswith(f"ext_{ident}_")])
        self.assertNotIn(ident, engine.VAULT.load()["tokens"])

    def test_plaintext_tokens_from_the_old_store_are_migrated(self):
        ident = store.add("Calendario", self.url, TOKEN, False)
        self.assertEqual(asyncio.run(rust_service.sync_one(ident)), 3)
        self.assertEqual(store.load()[ident]["token"], "")
        self.assertTrue(store.public(ident, store.load()[ident])["has_token"])

    def test_panel_api(self):
        app = FastAPI()
        app.include_router(api.admin_routes)
        app.dependency_overrides.update({api.require_admin: lambda: "admin"})
        web = TestClient(app)
        self.assertEqual(web.post("/api/mcp/servers", json={"name": "x", "url": "ftp://no"}).status_code, 400)
        made = web.post("/api/mcp/servers", json={"name": "Calendario", "url": self.url, "token": TOKEN}).json()
        self.assertEqual((made["tools"], made["status"]), (3, "collegato"))
        listed = web.get("/api/mcp/servers").json()["servers"]
        self.assertNotIn(TOKEN, json.dumps(listed))
        self.assertEqual(web.post(f"/api/mcp/servers/{made['id']}/refresh").json()["tools"], 3)
        self.assertEqual(web.delete(f"/api/mcp/servers/{made['id']}").status_code, 200)
        self.assertEqual(web.delete(f"/api/mcp/servers/{made['id']}").status_code, 404)


if __name__ == "__main__":
    unittest.main()
