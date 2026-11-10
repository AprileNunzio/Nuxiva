import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from features.agency import tools
from features.agency.forge import registry as forge_registry
from features.agency.forge.registry import ForgedTool

SQUARE_CODE = "def run(args):\n    return args['x'] * args['x']\n"
TESTS = [{"args": {"x": 3}, "expect": 9}, {"args": {"x": 4}, "expect": 16}]


class ToolPermissionsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.project_dir = self.tmp / "workspace"
        self.project_dir.mkdir(parents=True, exist_ok=True)
        patcher = mock.patch.object(forge_registry.registry, "directory", self.tmp)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.registry = forge_registry.registry

    def square_tool(self, name: str = "quadrato") -> ForgedTool:
        return ForgedTool(
            name=name,
            description="calcola quadrato",
            args={"x": "number"},
            code=SQUARE_CODE,
            tests=TESTS,
            origin={"project": "shop", "task": "math"},
        )

    def run_tool(self, ctx: tools.Context, name: str, args: dict) -> str:
        return asyncio.run(tools.call(ctx, name, args))

    def test_revoked_worker_loses_all_tool_access(self) -> None:
        ctx = tools.Context(
            project_id="shop",
            folder=str(self.project_dir),
            task="t1",
            worker="w-1",
            generation=1,
            revoked=True,
        )
        res = self.run_tool(ctx, "write_file", {"path": "a.txt", "content": "hello"})
        self.assertIn("worker assignment revoked", res)
        self.assertFalse((self.project_dir / "a.txt").exists())

    def test_permission_denied_when_capability_missing(self) -> None:
        ctx = tools.Context(
            project_id="shop",
            folder=str(self.project_dir),
            task="t1",
            worker="w-1",
            generation=1,
            permissions=["read"],
        )
        res_write = self.run_tool(ctx, "write_file", {"path": "test.txt", "content": "data"})
        self.assertIn("permission denied for capability 'write'", res_write)
        res_exec = self.run_tool(ctx, "run_check", {"check": "python_tests"})
        self.assertIn("permission denied for capability 'execute'", res_exec)
        self.assertFalse((self.project_dir / "test.txt").exists())

    def test_path_traversal_is_blocked(self) -> None:
        ctx = tools.Context(
            project_id="shop",
            folder=str(self.project_dir),
            task="t1",
            permissions=["read", "write"],
        )
        res_write = self.run_tool(ctx, "write_file", {"path": "../outside.txt", "content": "evil"})
        self.assertIn("error", res_write)
        self.assertFalse((self.tmp / "outside.txt").exists())

    def test_versioned_proposal_and_approval_cycle(self) -> None:
        tool = self.square_tool("calc_sq")
        proposed = self.registry.propose(tool)
        self.assertEqual(proposed.version, 1)
        self.assertEqual(proposed.status, forge_registry.PROPOSED)
        self.assertFalse(proposed.approved)
        self.assertIsNone(self.registry.by_call_name("x_calc_sq"))

        ctx = tools.Context(
            project_id="shop",
            folder=str(self.project_dir),
            task="t1",
            permissions=["read", "write", "execute"],
        )
        with mock.patch("features.agency.forge.sandbox.execute", return_value={"ok": True, "result": 25}):
            res_unapproved = self.run_tool(ctx, "x_calc_sq", {"x": 5})
            self.assertIn("revoked or not approved", res_unapproved)

            approved = self.registry.approve("calc_sq")
            self.assertEqual(approved.status, forge_registry.ACTIVE)
            self.assertTrue(approved.approved)
            self.assertIsNotNone(self.registry.by_call_name("x_calc_sq"))

            res_approved = self.run_tool(ctx, "x_calc_sq", {"x": 5})
            self.assertEqual(res_approved, "25")

            self.registry.revoke("calc_sq", reason="policy breach")
            res_revoked = self.run_tool(ctx, "x_calc_sq", {"x": 5})
            self.assertIn("revoked or not approved", res_revoked)


if __name__ == "__main__":
    unittest.main()
