import asyncio
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import native_core
from agenti.agent import fs_mcp, paths, registry, tools_files
from agenti.mcpclient import calls, engine, store
from agenti.shares import archive
from sealed import SealedFile

ENABLED = native_core.symbol("RustMcpEngine") is not None and native_core.symbol("RustMcpEngine") is not None


def run(coro):
    return asyncio.run(coro)


def normal(text: str, base: Path) -> str:
    text = text.replace(str(base), "<B>")
    text = re.sub(r"modificato il .*", "modificato", text)
    text = re.sub(r"cestino: .*", "cestino", text)
    return text


class Isolated(unittest.TestCase):
    def build(self, mode: str):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        base = Path(os.path.realpath(folder.name))
        work, models, trash, files = base / "work", base / "models", base / "trash", base / "work" / "condivisa" / "documenti"
        for directory in (work, models, files):
            directory.mkdir(parents=True)
        patches = [mock.patch.object(paths, "WORK", work), mock.patch.object(paths, "MODELS", models), mock.patch.object(paths, "TRASH", trash),
                   mock.patch.object(paths, "FILES", files), mock.patch.object(tools_files, "FILES", files), mock.patch.object(tools_files, "TRASH", trash),
                   mock.patch.object(archive, "ROOT", work / "condivisa"), mock.patch.object(store, "FILE", base / "s.json"),
                   mock.patch.object(engine, "VAULT", SealedFile(base / "v.vault", base / "v.key")), mock.patch.object(engine, "SETTINGS_FILE", base / "a.json"),
                   mock.patch.object(engine, "POLICY_FILE", base / "b.json"), mock.patch.object(engine, "SCOPES_FILE", base / "c.json"),
                   mock.patch.object(engine, "INTERNAL_FILE", base / "d.json"), mock.patch.object(engine, "AUDIT_FILE", base / "audit.log"),
                   mock.patch.dict(os.environ, {fs_mcp.AREA: mode, "NUXIVA_MCP_ENGINE": "rust"})]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(engine.shutdown)
        self.addCleanup(calls.ASKED.clear)
        token = registry.REQUEST.set("organizza i file")
        self.addCleanup(registry.REQUEST.reset, token)
        return base


@unittest.skipUnless(ENABLED, "modulo nativo non disponibile")
class ParityTest(Isolated):
    def step(self, name: str, **args) -> str:
        registry.needs_confirm(name, args)
        return run(registry.TOOLS[name]["fn"](**args))

    def scenario(self, mode: str) -> list[str]:
        base = self.build(mode)
        w = base / "work"
        out = [
            self.step("write_file", path=str(w / "a.txt"), content="uno\ndue"),
            self.step("write_file", path=str(w / "a.txt"), content="+tre", append="true"),
            self.step("read_file", path=str(w / "a.txt")),
            self.step("make_dir", path=str(w / "x" / "y")),
            self.step("write_file", path=str(w / "x" / "y" / "f.md"), content="ciao"),
            self.step("copy", src=str(w / "x"), dst=str(w / "z")),
            self.step("list_dir", path=str(w)),
            self.step("list_dir", path=""),
            self.step("move", src=str(w / "z"), dst=str(w / "k")),
            self.step("file_info", path=str(w / "a.txt")),
            self.step("delete", path=str(w / "k")),
            self.step("list_dir", path=str(w)),
        ]
        out.append("\n".join(sorted(self.step("find_files", pattern="f", root=str(w)).splitlines())))
        return [normal(item, base) for item in out]

    def test_every_file_tool_gives_the_same_result_on_both_engines(self):
        legacy = self.scenario("legacy")
        engine.shutdown()
        mcp = self.scenario("mcp")
        self.assertEqual(len(legacy), len(mcp))
        for index, (a, b) in enumerate(zip(legacy, mcp)):
            with self.subTest(step=index):
                self.assertEqual(a, b)

    def test_mcp_mode_never_reaches_outside_the_roots(self):
        base = self.build("mcp")
        outside = base / "fuori.txt"
        outside.write_text("riservato", encoding="utf-8")
        for call in (lambda: tools_files.read_file(str(outside)), lambda: tools_files.write_file(str(outside), "x"),
                     lambda: tools_files.read_file(str(base / "work" / ".." / "fuori.txt")), lambda: tools_files.delete(str(outside))):
            with self.assertRaises(Exception):
                run(call())
        self.assertEqual(outside.read_text(encoding="utf-8"), "riservato")

    def test_delete_asks_for_confirmation_and_then_runs_once(self):
        base = self.build("mcp")
        target = base / "work" / "d.txt"
        target.write_text("x", encoding="utf-8")
        self.assertTrue(registry.needs_confirm("delete", {"path": str(target)}))
        run(tools_files.delete(str(target)))
        self.assertFalse(target.exists())
        target.write_text("x", encoding="utf-8")
        calls.ASKED.clear()
        with self.assertRaises(PermissionError):
            run(tools_files.delete(str(target)))
        self.assertTrue(target.exists())

    def test_plain_writes_inside_the_roots_need_no_confirmation(self):
        base = self.build("mcp")
        fs_mcp.ensure()
        self.assertTrue(engine.wait_tool("files.write_file"))
        self.assertFalse(registry.needs_confirm("write_file", {"path": str(base / "work" / "n.txt")}))
        self.assertFalse(registry.needs_confirm("read_file", {"path": str(base / "work" / "n.txt")}))

    def test_legacy_mode_is_the_default_and_never_touches_the_engine(self):
        base = self.build("legacy")
        run(tools_files.write_file(str(base / "work" / "l.txt"), "ok"))
        self.assertFalse(engine.published())
        self.assertFalse(registry.needs_confirm("read_file", {"path": str(base / "work" / "l.txt")}))


if __name__ == "__main__":
    unittest.main()
