import json
import unittest
from types import SimpleNamespace
from unittest import mock

from features.selftest import sandbox_check
from features.selftest.skip import Skip


class SandboxSelftestTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        patches = [mock.patch.object(sandbox_check, "DEMO", False),
                   mock.patch.object(sandbox_check, "os", SimpleNamespace(name="posix", environ={})),
                   mock.patch.object(sandbox_check.store, "steps", {"sandbox": {"status": "on_demand"}}),
                   mock.patch.object(sandbox_check.packages, "step_wanted", return_value=False),
                   mock.patch.object(sandbox_check, "Path"),
                   mock.patch.object(sandbox_check.asyncio, "create_subprocess_exec", new_callable=mock.AsyncMock)]
        self.mocks = [patch.start() for patch in patches]
        for patch in patches:
            self.addCleanup(patch.stop)
        self.mocks[4].return_value.exists.return_value = False
        self.process = mock.Mock()
        self.process.communicate = mock.AsyncMock(return_value=(json.dumps({"ok": False, "problems": ["broker unreachable"]}).encode(), b""))
        self.mocks[-1].return_value = self.process

    async def test_unrequested_on_demand_package_is_not_reported_as_healthy(self):
        with self.assertRaisesRegex(Skip, "isolamento non verificato"):
            await sandbox_check.sandbox_isolation()
        self.mocks[-1].assert_not_called()

    async def test_requested_missing_broker_still_fails(self):
        self.mocks[3].return_value = True
        with self.assertRaisesRegex(AssertionError, "broker unreachable"):
            await sandbox_check.sandbox_isolation()

    async def test_failed_installation_still_fails(self):
        sandbox_check.store.steps["sandbox"]["status"] = "failed"
        with self.assertRaisesRegex(AssertionError, "broker unreachable"):
            await sandbox_check.sandbox_isolation()

    async def test_existing_socket_still_requires_actual_isolation_probe(self):
        self.mocks[4].return_value.exists.return_value = True
        with self.assertRaisesRegex(AssertionError, "broker unreachable"):
            await sandbox_check.sandbox_isolation()
