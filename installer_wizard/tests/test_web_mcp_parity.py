import asyncio
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

import native_core
from agenti.agent import registry, tools_system, web_mcp
from agenti.mcpclient import calls, engine, store
from sealed import SealedFile

ENABLED = native_core.symbol("RustMcpEngine") is not None
PAGE = "<html><head><style>p{color:red}</style><script>var x=1;</script></head><body><h1>Titolo</h1><p>Ciao   mondo</p></body></html>"
BIG = "<p>" + "parola " * 2000 + "</p>"


class Origin(BaseHTTPRequestHandler):
    def log_message(self, *args) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/jump":
            self.send_response(302)
            self.send_header("Location", "/page")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        body = {"/page": PAGE, "/big": BIG}.get(self.path)
        self.send_response(200 if body is not None else 404)
        data = (body or "").encode()
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def run(coro):
    return asyncio.run(coro)


@unittest.skipUnless(ENABLED, "modulo nativo non disponibile")
class WebParityTest(unittest.TestCase):
    def build(self, mode: str, config: dict | None = None) -> str:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        base = Path(os.path.realpath(folder.name))
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), Origin)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(httpd.server_close)
        self.addCleanup(httpd.shutdown)
        allow = {"hosts": ["127.0.0.1"], "network": {"allow_loopback": True, "ports": []}} if config is None else config
        patches = [mock.patch.object(store, "FILE", base / "s.json"), mock.patch.object(engine, "VAULT", SealedFile(base / "v.vault", base / "v.key")),
                   mock.patch.object(engine, "SETTINGS_FILE", base / "a.json"), mock.patch.object(engine, "POLICY_FILE", base / "b.json"),
                   mock.patch.object(engine, "SCOPES_FILE", base / "c.json"), mock.patch.object(engine, "INTERNAL_FILE", base / "d.json"),
                   mock.patch.object(engine, "AUDIT_FILE", base / "audit.log"),
                   mock.patch.dict(engine.INTERNAL, {web_mcp.SERVER: lambda: {"id": web_mcp.SERVER, "kind": "fetch", "config": allow}}),
                   mock.patch.dict(os.environ, {web_mcp.AREA: mode, "NUXIVA_MCP_ENGINE": "rust"})]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(engine.shutdown)
        self.addCleanup(calls.ASKED.clear)
        token = registry.REQUEST.set("leggi la pagina")
        self.addCleanup(registry.REQUEST.reset, token)
        return f"http://127.0.0.1:{httpd.server_address[1]}"

    def fetch(self, url: str) -> str:
        registry.needs_confirm("http_get", {"url": url})
        return run(registry.TOOLS["http_get"]["fn"](url=url))

    def scenario(self, mode: str) -> list[str]:
        base = self.build(mode)
        return [self.fetch(f"{base}{path}") for path in ("/page", "/missing", "/jump", "/big")]

    def test_pages_give_the_same_text_on_both_engines(self):
        legacy = self.scenario("legacy")
        engine.shutdown()
        mcp = self.scenario("mcp")
        self.assertEqual([item.strip() for item in legacy], [item.strip() for item in mcp])
        self.assertEqual(mcp[0], "HTTP 200\nTitolo Ciao mondo")

    def test_mcp_mode_denies_local_and_metadata_targets_by_default(self):
        self.build("mcp", config={})
        for url in ("http://127.0.0.1:9/", "http://169.254.169.254/latest", "file:///etc/passwd", "http://10.0.0.1/"):
            with self.assertRaises(RuntimeError):
                self.fetch(url)

    def test_legacy_mode_never_touches_the_engine(self):
        base = self.build("legacy")
        self.fetch(f"{base}/page")
        self.assertFalse(engine.published())
        self.assertFalse(registry.needs_confirm("http_get", {"url": f"{base}/page"}))

    def test_the_wrapper_is_the_registered_tool(self):
        self.assertIs(registry.TOOLS["http_get"]["fn"], tools_system.http_get)
