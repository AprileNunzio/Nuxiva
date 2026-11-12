import importlib
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from agenti.agent import registry, tool_scanner

TOOL = '''from agenti.agent.registry import tool


@tool("zz_probe_tool", "strumento di prova", {}, agent="zz_probe")
async def zz_probe_tool() -> str:
    return "ok"


@tool("zz_probe_sync", "strumento sincrono", {}, agent="zz_probe")
def zz_probe_sync() -> str:
    return "sincrono"
'''


class ToolScannerTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.pkg = base / "zzfeatures"
        self.root = self.pkg / "creativita"
        self.root.mkdir(parents=True)
        (self.pkg / "__init__.py").write_text(f"__path__ = [{str(self.root)!r}]\n")
        sys.path.insert(0, str(base))
        self.addCleanup(sys.path.remove, str(base))
        for target, value in (("AGENTS_DIR", self.pkg), ("PACKAGE", "zzfeatures")):
            patcher = unittest.mock.patch.object(tool_scanner, target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.saved_tools = dict(registry.TOOLS)
        self.saved_loaded = dict(tool_scanner._loaded)
        self.saved_modules = {m: sys.modules[m] for m in tool_scanner._loaded if m in sys.modules}
        self.addCleanup(self.restore)

    def restore(self):
        registry.TOOLS.clear()
        registry.TOOLS.update(self.saved_tools)
        tool_scanner._loaded.clear()
        tool_scanner._loaded.update(self.saved_loaded)
        tool_scanner._failed.clear()
        tool_scanner._signature = ""
        sys.modules.update(self.saved_modules)
        for name in [m for m in sys.modules if m.startswith("zzfeatures")]:
            del sys.modules[name]
        importlib.invalidate_caches()

    def add_feature(self, source=TOOL, manifest=True):
        folder = self.root / "zz_probe"
        folder.mkdir(exist_ok=True)
        (folder / "__init__.py").write_text("")
        (folder / "tools.py").write_text(source)
        if manifest:
            (folder / "feature.json").write_text("{}")
        importlib.invalidate_caches()

    async def test_new_feature_tools_appear_and_disappear_live(self):
        self.assertNotIn("zz_probe_tool", registry.TOOLS)
        self.add_feature()
        self.assertTrue(tool_scanner.sync(force=True))
        self.assertEqual(registry.TOOLS["zz_probe_tool"]["feature"], "zz_probe")
        self.assertEqual(await registry.run("zz_probe_tool", {}), "ok")
        self.assertEqual(await registry.run("zz_probe_sync", {}), "sincrono")
        (self.root / "zz_probe" / "tools.py").unlink()
        tool_scanner.sync(force=True)
        self.assertNotIn("zz_probe_tool", registry.TOOLS)
        self.assertNotIn("zzfeatures.zz_probe.tools", tool_scanner.loaded())

    async def test_tools_package_is_discovered_and_unloaded(self):
        folder = self.root / "zz_probe"
        (folder / "tools").mkdir(parents=True)
        (folder / "__init__.py").write_text("")
        (folder / "feature.json").write_text("{}")
        (folder / "tools" / "zz_probe_tools.py").write_text(TOOL)
        (folder / "tools" / "__init__.py").write_text("from zzfeatures.zz_probe.tools import zz_probe_tools\n")
        importlib.invalidate_caches()
        tool_scanner.sync(force=True)
        self.assertEqual(registry.TOOLS["zz_probe_tool"]["feature"], "zz_probe")
        self.assertEqual(await registry.run("zz_probe_tool", {}), "ok")
        (folder / "tools" / "__init__.py").unlink()
        tool_scanner.sync(force=True)
        self.assertNotIn("zz_probe_tool", registry.TOOLS)
        self.assertNotIn("zzfeatures.zz_probe.tools.zz_probe_tools", sys.modules)

    def test_empty_tools_package_is_not_imported(self):
        folder = self.root / "zz_probe"
        (folder / "tools").mkdir(parents=True)
        (folder / "__init__.py").write_text("raise RuntimeError('non importare')\n")
        (folder / "feature.json").write_text("{}")
        (folder / "tools" / "__init__.py").write_text("TOOLS: tuple = ()\n")
        importlib.invalidate_caches()
        tool_scanner.sync(force=True)
        self.assertNotIn("zzfeatures.zz_probe.tools", tool_scanner.failed())
        self.assertNotIn("zzfeatures.zz_probe.tools", tool_scanner.loaded())

    def test_folder_without_manifest_is_not_a_feature(self):
        self.add_feature(manifest=False)
        tool_scanner.sync(force=True)
        self.assertNotIn("zz_probe_tool", registry.TOOLS)

    def test_broken_module_is_reported_not_fatal(self):
        self.add_feature(source="raise RuntimeError('boom')\n")
        tool_scanner.sync(force=True)
        self.assertEqual(tool_scanner.failed().get("zzfeatures.zz_probe.tools"), "RuntimeError")
        self.assertNotIn("zz_probe_tool", registry.TOOLS)


if __name__ == "__main__":
    unittest.main()
