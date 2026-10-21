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

    def test_local_setup_reopens_only_when_confirmed(self):
        calls = []
        control = describe("server", "server", self.loader)
        self.assertIn("setup", control.commands)
        with self.assertRaises(NodeCommandError) as ctx:
            execute(control, "setup", False, self.scheduled.append, self.loader, reopen_setup=lambda: calls.append(1))
        self.assertEqual(ctx.exception.status, 428)
        result = execute(control, "setup", True, self.scheduled.append, self.loader, reopen_setup=lambda: calls.append(1))
        self.assertEqual(result["status"], "executing")
        self.assertEqual(calls, [1])
        self.assertEqual(self.scheduled, [])

    def test_paired_nodes_cannot_reopen_server_setup(self):
        control = describe("sat-cucina", "server", self.loader)
        with self.assertRaises(NodeCommandError) as ctx:
            execute(control, "setup", True, self.scheduled.append, self.loader, reopen_setup=lambda: None)
        self.assertEqual(ctx.exception.status, 409)

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


class NodeCommandApiTests(unittest.TestCase):
    def test_local_commands_answer_through_the_real_endpoint(self):
        from unittest import mock
        from fastapi.testclient import TestClient
        import nuxiva_supervisor
        import node_commands_api
        import setup_api
        from server.features.mesh_coordinator.p2p_mesh import p2p_mesh

        self.addCleanup(setup_api.SETUP_FILE.unlink, missing_ok=True)
        client = TestClient(nuxiva_supervisor.admin)
        headers = {"X-Nuxiva-Request": "1"}
        client.post("/api/auth/login", json={"username": "admin", "password": "nuxiva"}, headers=headers)
        scheduled = []
        with mock.patch.object(node_commands_api, "delayed", side_effect=lambda *cmd: scheduled.append(cmd) or _noop()):
            for command in ("restart", "reboot", "setup"):
                with self.subTest(command=command):
                    r = client.post(f"/api/v5/nodes/{p2p_mesh.node_id}/commands/{command}", json={"confirm": True}, headers=headers)
                    self.assertEqual(r.status_code, 200, r.text)
                    self.assertEqual(r.json()["status"], "executing")
        self.assertEqual(scheduled, [("systemctl", "restart", "nuxiva-supervisor"), ("systemctl", "reboot")])


async def _noop():
    return None
