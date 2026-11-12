import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

import nuxiva_supervisor
from features.agency import tools
from features.agency.forge import guard, sandbox, smith
from features.agency.forge import registry as forge_registry
from features.agency.forge.registry import ForgedTool
from features.brain.llm import BrainUnavailable

HEADERS = {"X-Nuxiva-Request": "1"}
SQUARE = "def run(args):\n    return args['x'] * args['x']\n"
SPEC = {"name": "ignored", "description": "Quadrato di un numero", "args": {"x": "numero"}, "code": SQUARE,
        "tests": [{"args": {"x": 3}, "expect": 9}, {"args": {"x": -2}, "expect": 4}]}
needs_sandbox = unittest.skipUnless(sandbox.available(), "unshare is not available")


def scripted(*replies):
    queue = list(replies)

    async def generate(prompt, **kwargs):
        if not queue:
            raise BrainUnavailable("script finished")
        item = queue.pop(0)
        return item(prompt, kwargs) if callable(item) else item
    return generate


class ForgeCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        patcher = mock.patch.object(forge_registry.registry, "directory", self.tmp)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.registry = forge_registry.registry

    def square(self, name="quadrato"):
        return ForgedTool(name=name, description="q", args={"x": "n"}, code=SQUARE, tests=SPEC["tests"], origin={})


class GuardTest(unittest.TestCase):
    def test_accepts_pure_code(self):
        guard.check("import math\nfrom statistics import mean\n\ndef run(args):\n    return math.floor(mean(args['v']))\n")

    def test_rejects_escapes(self):
        for code in (
            "import os\ndef run(args):\n    return 1",
            "from subprocess import run as r\ndef run(args):\n    return 1",
            "def run(args):\n    return ().__class__",
            "def run(args):\n    return getattr(args, 'x')",
            "import typing\ndef run(args):\n    return typing.sys",
            "import dataclasses\ndef run(args):\n    return dataclasses.inspect",
            "def run(args):\n    return '{0.x}'.format(args)",
            "import operator\ndef run(args):\n    return operator.attrgetter('x')(args)",
            "def run(args):\n    return '__class__'",
            "def run(args):\n    return open('/etc/passwd').read()",
            "def run(args):\n    print(args)",
            "from math import *\ndef run(args):\n    return 1",
            "async def run(args):\n    return 1",
            "def run(a, b):\n    return 1",
            "def other(args):\n    return 1",
            "def run(args)\n    return 1",
            "",
        ):
            with self.subTest(code=code), self.assertRaises(guard.ForgeRejected):
                guard.check(code)

    def test_names(self):
        self.assertEqual(guard.name("somma_iva"), "somma_iva")
        for bad in ("A", "x", "1abc", "rm -rf", None, "a" * 41):
            with self.assertRaises(guard.ForgeRejected):
                guard.name(bad)


@needs_sandbox
class SandboxTest(unittest.TestCase):
    def test_runs_in_isolation(self):
        self.assertEqual(asyncio.run(sandbox.execute(SQUARE, {"x": 7})), {"ok": True, "result": 49})

    def test_errors_and_timeouts_are_reported(self):
        failed = asyncio.run(sandbox.execute("def run(args):\n    return 1 / 0\n", {}))
        self.assertFalse(failed["ok"])
        self.assertIn("ZeroDivisionError", failed["error"])
        with mock.patch.object(sandbox, "TIMEOUT", 1.0):
            looped = asyncio.run(sandbox.execute("def run(args):\n    while True:\n        pass\n", {}))
        self.assertFalse(looped["ok"])

    def test_unchecked_code_never_runs(self):
        with self.assertRaises(guard.ForgeRejected):
            asyncio.run(sandbox.execute("import os\ndef run(args):\n    return os.getcwd()\n", {}))


class RegistryTest(ForgeCase):
    def test_storage_is_encrypted_and_names_are_unique(self):
        self.registry.add(self.square())
        self.assertNotIn(b"args['x']", (self.tmp / "forge.sealed").read_bytes())
        self.assertEqual(self.registry.by_call_name("x_quadrato").name, "quadrato")
        self.assertIsNone(self.registry.by_call_name("quadrato"))
        with self.assertRaises(guard.ForgeRejected):
            self.registry.add(self.square())

    def test_unreliable_tools_retire_and_can_be_restored(self):
        self.registry.add(self.square())
        for _ in range(forge_registry.RETIRE_FAILS):
            self.registry.record("quadrato", False, "boom")
        tool = self.registry.get("quadrato")
        self.assertEqual((tool.status, tool.retired_reason), (forge_registry.RETIRED, "unreliable"))
        self.assertIsNone(self.registry.by_call_name("x_quadrato"))
        restored = self.registry.set_status("quadrato", forge_registry.ACTIVE)
        self.assertEqual((restored.status, restored.fails), (forge_registry.ACTIVE, 0))

    def test_active_limit(self):
        with mock.patch.object(forge_registry, "MAX_ACTIVE", 1):
            self.registry.add(self.square("uno_uno"))
            with self.assertRaises(guard.ForgeRejected):
                self.registry.add(self.square("due_due"))


@needs_sandbox
class SmithTest(ForgeCase):
    ARGS = {"name": "quadrato", "purpose": "quadrato di x", "example": "x=3 -> 9"}

    def test_retries_after_a_failing_test_then_registers(self):
        wrong = {**SPEC, "tests": [{"args": {"x": 3}, "expect": 10}, {"args": {"x": 1}, "expect": 1}]}
        seen = []

        def fixed(prompt, kwargs):
            seen.append(prompt)
            return SPEC
        with mock.patch("features.brain.llm.generate", scripted(wrong, fixed)):
            tool, tokens = asyncio.run(smith.forge(self.ARGS, {"project": "p"}))
        self.assertEqual(tool.name, "quadrato")
        self.assertIn("expected 10", seen[0])
        self.assertGreater(tokens, 0)
        self.assertEqual(self.registry.get("quadrato").origin, {"project": "p"})

    def test_gives_up_without_registering(self):
        unsafe = {**SPEC, "code": "import os\ndef run(args):\n    return 1\n"}
        with mock.patch("features.brain.llm.generate", scripted(unsafe, {**SPEC, "tests": []})):
            with self.assertRaises(guard.ForgeRejected):
                asyncio.run(smith.forge(self.ARGS, {}))
        self.assertEqual(self.registry.all(), [])

    def test_comparison_is_strict_on_types(self):
        self.assertTrue(smith.same([1, {"a": 2.0}], [1, {"a": 2}]))
        self.assertFalse(smith.same(True, 1))
        self.assertFalse(smith.same({"a": 1}, {"a": 1, "b": 2}))


@needs_sandbox
class ForgeToolsTest(ForgeCase):
    def use(self, ctx, name, args):
        return asyncio.run(tools.call(ctx, name, args))

    def test_agent_forges_then_calls_the_new_tool(self):
        ctx = tools.Context("shop", "shop", task="IVA")
        with mock.patch("features.brain.llm.generate", scripted(SPEC)):
            created = self.use(ctx, "forge_tool", {"name": "quadrato", "purpose": "q", "example": "3 -> 9"})
        self.assertTrue(created.startswith("created x_quadrato"))
        self.assertEqual(ctx.forged, ["quadrato"])
        self.assertIn("x_quadrato", [t["name"] for t in tools.manifest()])
        self.assertEqual(self.use(ctx, "x_quadrato", {"x": 5}), "25")
        self.assertTrue(self.use(ctx, "x_quadrato", {}).startswith("error: KeyError"))
        tool = self.registry.get("quadrato")
        self.assertEqual((tool.uses, tool.fails), (1, 1))

    def test_forging_is_bounded_and_can_be_disabled(self):
        ctx = tools.Context("shop", "shop")
        with mock.patch("features.brain.llm.generate", scripted({}, {}, {}, {})):
            for _ in range(tools.FORGES_PER_TASK):
                self.assertTrue(self.use(ctx, "forge_tool", {"name": "nulla_qui"}).startswith("error: tool not created"))
        self.assertIn("at most", self.use(ctx, "forge_tool", {"name": "nulla_qui"}))
        with mock.patch.object(tools.feature, "forge_enabled", return_value=False):
            self.assertIn("disabled", self.use(tools.Context("p", "p"), "forge_tool", {"name": "abc"}))
            self.assertNotIn("forge_tool", [t["name"] for t in tools.manifest()])


class ForgeApiTest(ForgeCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = TestClient(nuxiva_supervisor.admin)
        assert cls.admin.post("/api/auth/login", json={"username": "admin", "password": "nuxiva"}, headers=HEADERS).status_code == 200

    def test_list_retire_restore_delete(self):
        self.registry.add(self.square())
        listed = self.admin.get("/api/agency/tools").json()["tools"]
        self.assertEqual([t["call_name"] for t in listed], ["x_quadrato"])
        self.assertNotIn("code", listed[0])
        self.assertIn("args['x']", self.admin.get("/api/agency/tools/quadrato").json()["code"])
        retired = self.admin.post("/api/agency/tools/quadrato/retire", headers=HEADERS).json()
        self.assertEqual(retired["status"], "retired")
        self.assertEqual(self.admin.post("/api/agency/tools/quadrato/restore", headers=HEADERS).json()["status"], "active")
        self.assertEqual(self.admin.post("/api/agency/tools/quadrato/explode", headers=HEADERS).status_code, 400)
        self.assertEqual(self.admin.delete("/api/agency/tools/quadrato", headers=HEADERS).status_code, 200)
        missing = self.admin.get("/api/agency/tools/quadrato")
        self.assertEqual((missing.status_code, missing.json()["detail"]["code"]), (404, "tool_not_found"))
        self.assertEqual(self.admin.get("/api/agency/tools/Bad-Name").status_code, 404)


if __name__ == "__main__":
    unittest.main()
