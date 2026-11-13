import sys
import unittest
from unittest import mock

sys.modules.setdefault("cv2", mock.MagicMock())

import packages
from agenti.store import catalog as store_catalog
from agenti.store.catalog import STORE_CATALOG, get_catalog_with_status
from agenti.store.service import StoreManagerService
from state import store

SCENARIOS = (
    ({"NUXIVA_BRAIN": "cloud"}, True, {}),
    ({"NUXIVA_BRAIN": "cloud"}, False, {}),
    ({"NUXIVA_BRAIN": "local"}, False, {"ollama": "done", "brain": "done"}),
    ({"NUXIVA_BRAIN": "remote"}, False, {}),
    ({}, True, {}),
    ({}, False, {"ollama": "done"}),
    ({"NUXIVA_EAR": "1", "NUXIVA_MUSIC_ID": "on"}, False, {"ear": "done", "music": "running"}),
    ({"NUXIVA_VISION": "0", "NUXIVA_DOCUMENTS": "yes"}, False, {"vision": "done", "office": "failed"}),
    ({"NUXIVA_KIOSK": "", "NUXIVA_BLUETOOTH": "1", "NUXIVA_VOICESTUDIO": "1"}, False, {"bluetooth": "done", "voicestudio": "done"}),
)


class StoreParityTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        saved = {k: dict(v) for k, v in store.steps.items()}
        self.addCleanup(lambda: (store.steps.clear(), store.steps.update(saved)))
        for target in (mock.patch.object(packages, "DEMO", False),
                       mock.patch.object(packages, "ollama_remote", return_value=False),
                       mock.patch("brain_intent.cloud_provider", return_value="anthropic"),
                       mock.patch("brain_intent.required_local_models", return_value=())):
            target.start()
            self.addCleanup(target.stop)

    def _arrange(self, env: dict, engine: bool, steps: dict) -> None:
        for sid in packages.PACKAGE_BY_STEP:
            store.steps.pop(sid, None)
        for sid, status in steps.items():
            store.steps[sid] = {"status": status}
        for target in (mock.patch.object(packages, "read_env", lambda: dict(env)),
                       mock.patch.object(store_catalog, "read_env", lambda: dict(env)),
                       mock.patch("brain_intent.local_engine", return_value=engine)):
            target.start()
            self.addCleanup(target.stop)

    def test_every_store_item_is_backed_by_the_same_package(self):
        for item in STORE_CATALOG:
            with self.subTest(item=item.id):
                pkg = packages.PACKAGE_BY_ID[item.id]
                self.assertIs(item.package, pkg)
                self.assertEqual((item.env_key, item.steps, item.detect, item.removable),
                                 (pkg.env, pkg.steps, pkg.detect, pkg.removable))

    def test_both_stores_report_the_same_install_state(self):
        for env, engine, steps in SCENARIOS:
            with self.subTest(env=env, engine=engine, steps=steps):
                self._arrange(env, engine, steps)
                legacy = {row["id"]: row["state"] for row in packages.catalog()}
                for row in get_catalog_with_status():
                    self.assertEqual(row["state"], legacy[row["id"]])
                    self.assertEqual(row["installed"], legacy[row["id"]] == "installed")

    def test_cloud_brain_with_ollama_present_is_installed(self):
        self._arrange({"NUXIVA_BRAIN": "cloud"}, True, {})
        row = next(r for r in get_catalog_with_status() if r["id"] == "brain_local")
        self.assertTrue(row["installed"])

    def test_cloud_brain_without_ollama_is_not_installed(self):
        self._arrange({"NUXIVA_BRAIN": "cloud"}, False, {})
        row = next(r for r in get_catalog_with_status() if r["id"] == "brain_local")
        self.assertFalse(row["installed"])

    async def test_install_and_uninstall_send_the_same_request_as_the_legacy_store(self):
        service = StoreManagerService()
        for item in STORE_CATALOG:
            with self.subTest(item=item.id):
                apply = mock.AsyncMock(return_value=[])
                with mock.patch("agenti.store.service.apply_config", apply), \
                        mock.patch.object(service, "verify_resource_budget", return_value=(True, "ok")):
                    await service.install_package(item.id, user="admin")
                    apply.assert_awaited_once_with(packages.request_updates(item.id, True), "admin",
                                                   packages.request_steps(item.id))
                    if item.removable:
                        apply.reset_mock()
                        await service.uninstall_package(item.id, user="admin")
                        apply.assert_awaited_once_with(packages.request_updates(item.id, False), "admin",
                                                       packages.request_steps(item.id))


if __name__ == "__main__":
    unittest.main()
