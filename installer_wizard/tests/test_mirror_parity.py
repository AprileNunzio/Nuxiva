import asyncio
import contextvars
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import native_core
from agenti.agent import registry, tools_display
from agenti.mcpclient import calls, engine, mirror, store
from sealed import SealedFile

ENABLED = native_core.symbol("RustMcpEngine") is not None
PROBE = contextvars.ContextVar("probe", default="vuoto")
FLAG = "NUXIVA_MCP_AREA_READONLY"


def run(coro):
    return asyncio.run(coro)


@unittest.skipUnless(ENABLED, "modulo nativo non disponibile")
class MirrorTest(unittest.TestCase):
    def build(self, mode: str):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        base = Path(os.path.realpath(folder.name))
        patches = [mock.patch.object(store, "FILE", base / "s.json"), mock.patch.object(engine, "VAULT", SealedFile(base / "v.vault", base / "v.key")),
                   mock.patch.object(engine, "SETTINGS_FILE", base / "a.json"), mock.patch.object(engine, "POLICY_FILE", base / "b.json"),
                   mock.patch.object(engine, "SCOPES_FILE", base / "c.json"), mock.patch.object(engine, "INTERNAL_FILE", base / "d.json"),
                   mock.patch.object(engine, "AUDIT_FILE", base / "audit.log"), mock.patch.dict(os.environ, {FLAG: mode, "NUXIVA_MCP_ENGINE": "rust"})]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(engine.shutdown)
        self.addCleanup(calls.ASKED.clear)
        token = registry.REQUEST.set("che ore sono")
        self.addCleanup(registry.REQUEST.reset, token)
        mirror.install()
        patcher = mock.patch.dict(mirror.ORIGINALS)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_mirrored_tool_gives_the_same_result_through_rust(self):
        self.build("legacy")
        legacy = run(registry.TOOLS["list_models"]["fn"]())
        engine.shutdown()
        self.build("mcp")
        routed = run(registry.TOOLS["list_models"]["fn"]())
        self.assertEqual(legacy.strip(), routed.strip())
        self.assertTrue(engine.published())

    def test_context_variables_reach_the_original_tool(self):
        self.build("mcp")

        async def probe() -> str:
            return PROBE.get()
        mirror.ORIGINALS["now"] = probe

        async def scenario():
            PROBE.set("dal chiamante")
            return await registry.TOOLS["now"]["fn"]()
        self.assertEqual(run(scenario()), "dal chiamante")

    def test_tool_errors_are_reported_as_errors(self):
        self.build("mcp")

        async def boom() -> str:
            raise ValueError("guasto")
        mirror.ORIGINALS["now"] = boom
        with self.assertRaises(RuntimeError) as caught:
            run(registry.TOOLS["now"]["fn"]())
        self.assertIn("guasto", str(caught.exception))

    def test_unknown_contexts_and_arguments_are_refused(self):
        self.build("mcp")
        self.assertIn("is_error\": true", mirror.handle("readonly", "now", "{}", "inesistente"))
        with self.assertRaises(PermissionError):
            run(mirror.route("readonly", "now", {"extra": 1}))

    def test_catalog_is_consistent_with_the_registry(self):
        registry.refresh()
        mirror.install()
        seen: dict[str, str] = {}
        for server, area in mirror.AREAS.items():
            self.assertTrue(area["flag"].startswith("NUXIVA_MCP_AREA_"))
            for name, traits in area["tools"].items():
                self.assertIn(name, registry.TOOLS)
                self.assertNotIn(name, seen, f"{name} in {server} and {seen.get(name)}")
                seen[name] = server
                self.assertFalse(traits.get("read_only") and traits.get("destructive"))
                self.assertIn(name, mirror.ORIGINALS)

    def test_every_area_is_registered_and_gated(self):
        self.build("mcp")
        registry.refresh()
        for server in mirror.AREAS:
            definition = mirror.definition(server)
            self.assertIsNotNone(definition, server)
            self.assertEqual(definition["kind"], "mirror")
            self.assertTrue(definition["config"]["tools"])

    def test_destructive_tools_always_need_consent(self):
        self.build("mcp")
        with mock.patch.dict(os.environ, {"NUXIVA_MCP_AREA_EXEC": "mcp"}):
            registry.refresh()
            self.assertTrue(registry.needs_confirm("run_command", {"command": "ls"}))

    def test_legacy_mode_never_touches_the_engine(self):
        self.build("legacy")
        run(registry.TOOLS["now"]["fn"]())
        self.assertFalse(engine.published())
        self.assertFalse(registry.needs_confirm("now", {}))

    def test_wrappers_keep_the_signature_and_install_once(self):
        self.build("legacy")
        first = registry.TOOLS["now"]["fn"]
        mirror.install()
        self.assertIs(registry.TOOLS["now"]["fn"], first)
        self.assertTrue(hasattr(registry.TOOLS["list_models"]["fn"], "__wrapped__"))
        self.assertIs(tools_display.now, mirror.ORIGINALS["now"])
