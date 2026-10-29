import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from features.hardware import identify
from features.hardware.expert import HardwareAgent
from features.hardware.repos import OsInfo, RepoManager
from features.hardware.firmware import missing_for_device
from features.hardware.managed import ManagedDevices
from features.hardware.service import HardwareService
from . import agent_cases
from .common import dev


class PipelineFailureTest(unittest.TestCase):
    def setUp(self):
        self.agent = HardwareAgent()
        self.agent._pkg_manager = "apt"
        self.agent._repos = RepoManager(self.agent._run_cmd, OsInfo("debian", [], "13"), "/nonexistent")
        patcher = mock.patch("features.hardware.expert.shutil.which", return_value="tool")
        patcher.start()
        self.addCleanup(patcher.stop)

    def pipeline(self, **overrides):
        return agent_cases.AgentTest._mock_pipeline(self, **overrides)

    def test_failed_metadata_rolls_back_repositories_and_does_not_install(self):
        install = mock.AsyncMock(return_value=(0, "ok"))
        self.pipeline(update_packages=mock.AsyncMock(return_value=(1, "unavailable")), install_packages=install)
        device = dev(kernel_modules=["test_driver"])
        self.assertFalse(asyncio.run(self.agent.provision(device)))
        install.assert_not_awaited()
        self.assertEqual(device.status, "error")
        self.agent.repos.restore.assert_called_once_with(["/b"])
        self.assertEqual(device.capabilities, [])

    def test_failed_module_or_activation_never_becomes_ready(self):
        for override in ({"load_module_safely": mock.AsyncMock(return_value=(False, "module failed"))},
                         {"activate_device": mock.AsyncMock(return_value=False)}):
            self.pipeline(**override)
            device = dev(kernel_modules=["test_driver"])
            self.assertFalse(asyncio.run(self.agent.provision(device)))
            self.assertEqual(device.status, "error")
            self.assertEqual(device.capabilities, [])

    def test_disappeared_device_is_not_reported_ready(self):
        self.pipeline(_rebind=lambda device: None)
        device = dev(kernel_modules=["test_driver"])
        self.assertFalse(asyncio.run(self.agent.provision(device)))
        self.assertEqual(device.status, "error")

    def test_empty_package_candidates_do_not_report_installation_success(self):
        self.pipeline(filter_available=mock.AsyncMock(side_effect=lambda packages: ([], packages)))
        device = dev(kernel_modules=["test_driver"])
        self.assertFalse(asyncio.run(self.agent.provision(device)))
        self.assertEqual(device.status, "error")

    def test_failed_package_query_is_not_treated_as_available(self):
        self.agent._run_cmd = mock.AsyncMock(return_value=(1, "repository error"))
        packages, missing = asyncio.run(self.agent.filter_available(["firmware-realtek"]))
        self.assertEqual(packages, [])
        self.assertEqual(missing, ["firmware-realtek"])

    def test_package_options_never_reach_package_manager(self):
        self.agent._run_cmd = mock.AsyncMock()
        self.assertNotEqual(asyncio.run(self.agent.install_packages(["--allow-unauthenticated"]))[0], 0)
        self.agent._run_cmd.assert_not_awaited()

    def test_firmware_diagnostics_are_scoped_to_physical_device(self):
        output = "driver 0000:01:00.0: Direct firmware load for wifi.bin failed\ndriver 0000:02:00.0: Direct firmware load for other.bin failed\n"
        self.assertEqual(missing_for_device(output, dev(sys_id="0000:01:00.0"), lambda value: False), ["wifi.bin"])


class ServiceLifecycleTest(unittest.IsolatedAsyncioTestCase):
    async def test_duplicate_tasks_and_scan_preserve_current_operation(self):
        from features.hardware import service as hardware_module
        started, finish = asyncio.Event(), asyncio.Event()
        service = HardwareService()
        device = dev(status="needs_driver", kernel_modules=["test_driver"])
        service._devices[device.id] = device

        async def provision(current, **kwargs):
            started.set()
            await finish.wait()
            hardware_module.hardware_agent._set_status(current, "ready")
            return True

        with tempfile.TemporaryDirectory() as root, \
             mock.patch.object(hardware_module.hardware_agent, "provision", side_effect=provision), \
             mock.patch.object(service, "_publish_capabilities") as publish:
            service.managed = ManagedDevices(Path(root, "managed.json"))
            self.assertTrue(service.start_provisioning(device))
            self.assertFalse(service.start_provisioning(device))
            await started.wait()
            replacement = {device.id: dev(driver="test_driver")}
            service._merge(replacement)
            self.assertIs(replacement[device.id], device)
            finish.set()
            await asyncio.gather(*list(service._provisioning_tasks.values()))
            self.assertEqual(service._provisioning_tasks, {})
            self.assertIn(device.id, service.managed.load())
            self.assertGreaterEqual(publish.call_count, 2)

    async def test_auxiliary_bus_uses_kernel_aliases_without_recipe(self):
        with tempfile.TemporaryDirectory() as root:
            sysfs = Path(root)
            path = sysfs / "bus" / "i2c" / "devices" / "device1"
            path.mkdir(parents=True)
            (path / "modalias").write_text("i2c:example")
            alias = sysfs / "modules.alias"
            alias.write_text("alias i2c:example sensor_module\n")
            found = identify.scan_auxiliary(sysfs, identify.ModulesAlias(alias))
            self.assertEqual(found[0].kernel_modules, ["sensor_module"])
            self.assertEqual(found[0].bus, "i2c")

    def test_translations_share_status_keys(self):
        from features.hardware.localization import messages
        reference = set(messages("en"))
        for language in ("it", "fr", "es"):
            self.assertEqual(set(messages(language)), reference)
