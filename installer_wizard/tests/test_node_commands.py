import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
for p in (str(_ROOT), str(_ROOT / "installer_wizard"), str(_ROOT / "installer_wizard" / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from node_commands import NodeCommandError, describe, execute


class _FakeRegistry:
    def __init__(self):
        self.data = {"nodes": {"sat-cucina": {"id": "sat-cucina"}}}
        self.sent = []

    def command(self, node_id, command):
        self.sent.append((node_id, command))


class NodeCommandTests(unittest.TestCase):
    def setUp(self):
        self.registry = _FakeRegistry()
        self.loader = lambda: (self.registry, {"identify": "", "restart": "", "reboot": "", "update": "", "adapt": ""})
        self.scheduled = []

    def test_local_reboot_runs_systemctl_only_when_confirmed(self):
        control = describe("server", "server", self.loader)
        with self.assertRaises(NodeCommandError) as ctx:
            execute(control, "reboot", False, self.scheduled.append, self.loader)
        self.assertEqual(ctx.exception.status, 428)
        result = execute(control, "reboot", True, self.scheduled.append, self.loader)
        self.assertEqual(result["status"], "executing")
        self.assertEqual(self.scheduled, [("systemctl", "reboot")])

    def test_paired_reboot_is_queued_to_agent(self):
        control = describe("sat-cucina", "server", self.loader)
        self.assertEqual(control.scope, "paired")
        result = execute(control, "reboot", True, self.scheduled.append, self.loader)
        self.assertEqual(result["status"], "queued")
        self.assertEqual(self.registry.sent, [("sat-cucina", "reboot")])
        self.assertEqual(self.scheduled, [])

    def test_identify_needs_no_confirmation(self):
        control = describe("sat-cucina", "server", self.loader)
        execute(control, "identify", False, self.scheduled.append, self.loader)
        self.assertEqual(self.registry.sent, [("sat-cucina", "identify")])

    def test_unpaired_mesh_node_cannot_be_commanded(self):
        control = describe("ghost", "server", self.loader)
        self.assertEqual(control.commands, ())
        with self.assertRaises(NodeCommandError) as ctx:
            execute(control, "reboot", True, self.scheduled.append, self.loader)
        self.assertEqual(ctx.exception.status, 409)

    def test_unknown_command_rejected_for_local(self):
        control = describe("server", "server", self.loader)
        with self.assertRaises(NodeCommandError):
            execute(control, "rm", True, self.scheduled.append, self.loader)


if __name__ == "__main__":
    unittest.main()
