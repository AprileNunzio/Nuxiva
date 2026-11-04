import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from fastapi import HTTPException
from starlette.requests import Request

from features.authz import access_control as access
from features.authz.risk import Risk
from features.capabilities import mcp, tokens


class AccessControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "accounts.json"
        self.patch = mock.patch.object(access, "ACCOUNTS_FILE", self.path)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def write(self, value):
        self.path.write_text(json.dumps(value), encoding="utf-8")

    def test_scoped_auditor_cannot_read_another_node_or_manage_accounts(self):
        self.write({"alice": {"role": "auditor", "nodes": ["node-a"]}})
        access.require_permission("alice", "logs.read", "node-a")
        for permission, node in [("logs.read", "node-b"), ("api.admin", None), ("mcp.tools.execute", None)]:
            with self.assertRaises(HTTPException) as denied:
                access.require_permission("alice", permission, node)
            self.assertEqual(denied.exception.status_code, 403)

    def test_unclassified_api_defaults_to_administrator(self):
        self.write({"alice": {"role": "operator", "nodes": ["*"]}})
        request = Request({"type": "http", "route": SimpleNamespace(openapi_extra=None)})
        with self.assertRaises(HTTPException):
            access.authorize_request("alice", request)
        request.scope["route"].openapi_extra = {"x-nuxiva-capabilities": ["logs.read"]}
        access.authorize_request("alice", request)

    def test_corrupt_policy_fails_closed(self):
        for value in ["not json", '{"alice":{"role":"unknown"}}', '[]']:
            self.path.write_text(value, encoding="utf-8")
            with self.assertRaises(HTTPException) as error:
                access.account("root")
            self.assertEqual(error.exception.status_code, 503)

    def test_own_administrator_cannot_be_demoted(self):
        with self.assertRaises(HTTPException) as error:
            access.save_bindings({"alice": {"role": "viewer", "nodes": []}}, "alice")
        self.assertEqual(error.exception.status_code, 409)
        self.write({"alice": {"role": "administrator", "nodes": ["*"]}})
        with self.assertRaises(HTTPException):
            access.save_bindings({}, "alice")

    def test_unknown_permissions_and_roles_are_denied(self):
        self.assertFalse(access.allows("operator", "future.sensitive.operation"))
        self.assertFalse(access.allows("unknown", "logs.read"))
        self.assertEqual(access.principal_for_role("operator", "mcp:test").role, "family")

    def test_mcp_scope_and_role_are_both_required(self):
        available = [{"name": "read_one", "confirm": False}, {"name": "read_two", "confirm": False}]
        with mock.patch.object(mcp.registry, "available", return_value=available), mock.patch.object(mcp.roster, "owner", return_value="agent"), mock.patch.object(mcp.risk, "of_tool", return_value=Risk.INFO):
            self.assertEqual(mcp.visible({"risky": False, "role": "viewer"}), [])
            self.assertEqual(mcp.visible({"risky": False, "role": "operator", "allowed_tools": ["read_one"]}), ["read_one"])
            self.assertEqual(mcp.visible({"risky": True, "role": "operator", "allowed_tools": []}), [])

    def test_mcp_token_cannot_silently_escalate(self):
        with mock.patch.object(tokens, "FILE", Path(self.temp.name) / "tokens.json"):
            with self.assertRaises(ValueError):
                tokens.create("bad", role="administrator")
            for invalid in ("", 0, []):
                with self.assertRaises(ValueError):
                    tokens.create("invalid", role=invalid)
            with self.assertRaises(ValueError):
                tokens.create("invalid", risky="false")
            created = tokens.create("scoped", role="auditor", allowed_tools=["read_*"])
            checked = tokens.check("Bearer " + created["token"], "test-client")
            self.assertEqual(checked["role"], "auditor")
            self.assertEqual(checked["allowed_tools"], ["read_*"])


class MCPDeniedTests(unittest.IsolatedAsyncioTestCase):
    async def test_runner_receives_the_token_role_instead_of_system(self):
        token = {"id": "test", "risky": False, "role": "operator"}
        observed = []

        async def run(name, args):
            observed.append(mcp.current.get().role)
            return "done"

        with mock.patch.object(mcp, "visible", return_value=["now"]), mock.patch.object(mcp.schema, "input_schema", return_value={"required": []}), mock.patch.object(mcp.registry, "needs_confirm", return_value=False), mock.patch.object(mcp.runner, "run_as", side_effect=run), mock.patch.object(mcp.audit, "record"):
            result = await mcp.call({"name": "now"}, token)
        self.assertFalse(result["isError"])
        self.assertEqual(observed, ["family"])

    async def test_viewer_cannot_read_resources_or_call_tools(self):
        token = {"id": "test", "risky": False, "role": "viewer"}
        for method, params in [("resources/list", {}), ("tools/call", {"name": "anything"})]:
            with self.assertRaises(mcp.RpcError):
                await mcp.dispatch(method, params, token)
