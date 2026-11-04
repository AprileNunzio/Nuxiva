import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

sys.modules.setdefault("cv2", mock.MagicMock())

from access import require_admin
from fastapi.testclient import TestClient
from features.store.catalog import STORE_CATALOG, find_item
from features.store.repositories import (
    add_repository,
    get_custom_packages,
    load_repositories,
    remove_repository,
)
from features.store.service import StoreManagerService
import nuxiva_supervisor
import setup_api


class TestStoreCatalogAndService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = StoreManagerService()

    def test_catalog_structure_and_categories(self):
        self.assertTrue(len(STORE_CATALOG) >= 8)
        ids = {item.id for item in STORE_CATALOG}
        self.assertIn("music", ids)
        self.assertIn("ear", ids)
        self.assertIn("vision", ids)
        self.assertIn("brain_local", ids)
        categories = {item.category for item in STORE_CATALOG}
        self.assertIn("audio", categories)
        self.assertIn("intelligence", categories)

    def test_find_item(self):
        item = find_item("music")
        self.assertIsNotNone(item)
        self.assertEqual(item.id, "music")
        self.assertIsNone(find_item("non_existent_package"))

    def test_service_list_all(self):
        items = self.service.list_all()
        self.assertEqual(len(items), len(STORE_CATALOG))
        music_item = next(i for i in items if i["id"] == "music")
        self.assertIn("installed", music_item)

    def test_resource_budget_checks(self):
        with mock.patch("psutil.disk_usage") as mock_disk, mock.patch("psutil.virtual_memory") as mock_ram:
            mock_disk.return_value = mock.Mock(free=100 * (1024**3))
            mock_ram.return_value = mock.Mock(total=16 * (1024**3))
            ok, reason = self.service.verify_resource_budget("music")
            self.assertTrue(ok)
            self.assertEqual(reason, "ok")

            mock_disk.return_value = mock.Mock(free=0.1 * (1024**3))
            ok, reason = self.service.verify_resource_budget("music")
            self.assertFalse(ok)
            self.assertEqual(reason, "insufficient_disk_space")

            mock_disk.return_value = mock.Mock(free=100 * (1024**3))
            mock_ram.return_value = mock.Mock(total=4 * (1024**3))
            ok, reason = self.service.verify_resource_budget("brain_local")
            self.assertFalse(ok)
            self.assertEqual(reason, "insufficient_memory")

            ok_force, reason_force = self.service.verify_resource_budget("brain_local", force=True)
            self.assertTrue(ok_force)
            self.assertEqual(reason_force, "ok")

    async def test_install_memory_advisory_and_force(self):
        with mock.patch("psutil.disk_usage") as mock_disk, mock.patch("psutil.virtual_memory") as mock_ram:
            mock_disk.return_value = mock.Mock(free=100 * (1024**3))
            mock_ram.return_value = mock.Mock(total=4 * (1024**3))
            res = await self.service.install_package("brain_local", user="admin", force=False)
            self.assertFalse(res.get("ok"))
            self.assertTrue(res.get("advisory"))
            self.assertTrue(res.get("can_force"))
            self.assertIn("budget di memoria fisica", res.get("message", ""))

            with mock.patch("features.store.service.apply_config", mock.AsyncMock(return_value=["step1"])):
                res_forced = await self.service.install_package("brain_local", user="admin", force=True)
                self.assertTrue(res_forced.get("ok"))
                self.assertEqual(res_forced.get("id"), "brain_local")

    async def test_install_and_uninstall_package(self):
        with mock.patch("features.store.service.apply_config", mock.AsyncMock(return_value=["step1"])):
            with mock.patch.object(self.service, "verify_resource_budget", return_value=(True, "ok")):
                res = await self.service.install_package("music", user="admin")
                self.assertTrue(res.get("ok"))
                self.assertEqual(res.get("id"), "music")

                unres = await self.service.uninstall_package("music", user="admin")
                self.assertTrue(unres.get("ok"))
                self.assertEqual(unres.get("id"), "music")

    async def test_uninstall_non_removable_fails(self):
        brain_item = find_item("brain_local")
        self.assertFalse(brain_item.removable)
        res = await self.service.uninstall_package("brain_local", user="admin")
        self.assertFalse(res.get("ok"))
        self.assertEqual(res.get("error"), "package_not_removable")

    async def test_custom_repository_flow(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with mock.patch("features.store.repositories.STATE_DIR", tmp_path):
                repos = load_repositories()
                self.assertEqual(len(repos), 1)
                self.assertEqual(repos[0]["id"], "official")

                # Add a custom repository
                custom_pkgs = [{
                    "id": "my_tool",
                    "title": "Strumento Personalizzato",
                    "description": "Estensione creata dall'utente",
                    "category": "productivity",
                    "size_gb": 0.2
                }]
                new_repo = add_repository("Lab Personale", "https://example.com/repo.json", "Repo di test", packages=custom_pkgs)
                self.assertTrue(new_repo["id"].startswith("repo_"))
                self.assertEqual(new_repo["name"], "Lab Personale")

                all_repos = load_repositories()
                self.assertEqual(len(all_repos), 2)

                # Check custom package appears in catalog
                packages = self.service.list_all()
                self.assertTrue(any(p["id"] == f"{new_repo['id']}:my_tool" for p in packages))

                pkg_id = f"{new_repo['id']}:my_tool"
                # Install custom package
                res_inst = await self.service.install_package(pkg_id, user="admin")
                self.assertTrue(res_inst.get("ok"))
                self.assertTrue(res_inst.get("custom"))

                # Verify marked installed
                custom_items = get_custom_packages()
                installed_pkg = next(p for p in custom_items if p["id"] == pkg_id)
                self.assertTrue(installed_pkg["installed"])

                # Uninstall custom package
                res_uninst = await self.service.uninstall_package(pkg_id, user="admin")
                self.assertTrue(res_uninst.get("ok"))

                # Official repo deletion must fail
                with self.assertRaises(ValueError):
                    remove_repository("official")

                # Remove custom repo
                removed = remove_repository(new_repo["id"])
                self.assertTrue(removed)
                self.assertEqual(len(load_repositories()), 1)


class TestStoreEndpoints(unittest.TestCase):
    def setUp(self):
        nuxiva_supervisor.admin.dependency_overrides[require_admin] = lambda: "test_admin"
        self.client = TestClient(nuxiva_supervisor.admin)

    def tearDown(self):
        nuxiva_supervisor.admin.dependency_overrides.pop(require_admin, None)

    def test_get_store_packages(self):
        res = self.client.get("/api/store/packages")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("packages", data)
        self.assertIn("resources", data)
        self.assertIn("disk_free_gb", data["resources"])

    def test_get_single_package(self):
        res = self.client.get("/api/store/packages/music")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["id"], "music")
        self.assertIn("budget_ok", data)

    def test_get_invalid_package_404(self):
        res = self.client.get("/api/store/packages/unknown_pack")
        self.assertEqual(res.status_code, 404)

    def test_install_requires_csrf_header(self):
        res = self.client.post("/api/store/packages/music/install")
        self.assertEqual(res.status_code, 403)

    def test_install_success_with_csrf(self):
        headers = {"X-Nuxiva-Request": "1"}
        with mock.patch("features.store.service.apply_config", mock.AsyncMock(return_value=["step1"])):
            with mock.patch("features.store.service.store_service.verify_resource_budget", return_value=(True, "ok")):
                res = self.client.post("/api/store/packages/music/install", headers=headers)
                self.assertEqual(res.status_code, 200)
                self.assertTrue(res.json().get("ok"))

    def test_install_advisory_endpoint(self):
        headers = {"X-Nuxiva-Request": "1"}
        with mock.patch("psutil.disk_usage") as mock_disk, mock.patch("psutil.virtual_memory") as mock_ram:
            mock_disk.return_value = mock.Mock(free=100 * (1024**3))
            mock_ram.return_value = mock.Mock(total=4 * (1024**3))
            res = self.client.post("/api/store/packages/brain_local/install", headers=headers, json={"force": False})
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertFalse(data.get("ok"))
            self.assertTrue(data.get("advisory"))
            self.assertTrue(data.get("can_force"))

    def test_install_force_endpoint(self):
        headers = {"X-Nuxiva-Request": "1"}
        with mock.patch("psutil.disk_usage") as mock_disk, mock.patch("psutil.virtual_memory") as mock_ram:
            mock_disk.return_value = mock.Mock(free=100 * (1024**3))
            mock_ram.return_value = mock.Mock(total=4 * (1024**3))
            with mock.patch("features.store.service.apply_config", mock.AsyncMock(return_value=["step1"])):
                res = self.client.post("/api/store/packages/brain_local/install", headers=headers, json={"force": True})
                self.assertEqual(res.status_code, 200)
                data = res.json()
                self.assertTrue(data.get("ok"))

    def test_repositories_api_crud(self):
        headers = {"X-Nuxiva-Request": "1"}
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with mock.patch("features.store.repositories.STATE_DIR", tmp_path):
                # 1. Get repos
                res = self.client.get("/api/store/repositories")
                self.assertEqual(res.status_code, 200)
                data = res.json()
                self.assertIn("repositories", data)
                self.assertEqual(len(data["repositories"]), 1)
                self.assertEqual(data["repositories"][0]["id"], "official")

                # 2. Add repo
                new_repo_payload = {
                    "name": "Community Plugins",
                    "url": "https://plugins.community.local/manifest.json",
                    "description": "Moduli community",
                    "packages": [
                        {"id": "plugin_x", "title": "Plugin X", "category": "system", "size_gb": 0.1}
                    ]
                }
                res_post = self.client.post("/api/store/repositories", headers=headers, json=new_repo_payload)
                self.assertEqual(res_post.status_code, 201)
                created = res_post.json()["repository"]
                repo_id = created["id"]
                self.assertEqual(created["name"], "Community Plugins")

                # 3. Check packages endpoint contains custom package and repositories
                res_pkgs = self.client.get("/api/store/packages")
                self.assertEqual(res_pkgs.status_code, 200)
                pkgs_data = res_pkgs.json()
                self.assertIn("repositories", pkgs_data)
                self.assertEqual(len(pkgs_data["repositories"]), 2)
                self.assertTrue(any(p["id"] == f"{repo_id}:plugin_x" for p in pkgs_data["packages"]))

                # 4. Delete official repo should fail
                res_del_official = self.client.delete("/api/store/repositories/official", headers=headers)
                self.assertEqual(res_del_official.status_code, 400)

                # 5. Delete custom repo
                res_del = self.client.delete(f"/api/store/repositories/{repo_id}", headers=headers)
                self.assertEqual(res_del.status_code, 200)

                # 6. Repos list back to 1
                res_after = self.client.get("/api/store/repositories")
                self.assertEqual(len(res_after.json()["repositories"]), 1)


class TestSetupRewriteAndActivationSync(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.state_dir = Path(self.tmp_dir.name)
        self.patch_state = mock.patch("setup_api.STATE_DIR", self.state_dir)
        self.patch_file = mock.patch("setup_api.SETUP_FILE", self.state_dir / "setup.json")
        self.patch_state.start()
        self.patch_file.start()
        self.client = TestClient(nuxiva_supervisor.public)

    def tearDown(self):
        self.patch_state.stop()
        self.patch_file.stop()
        self.tmp_dir.cleanup()

    def test_setup_page_serves_html(self):
        with mock.patch("setup_api.is_local", return_value=True), mock.patch("setup_api.done", return_value=False):
            res = self.client.get("/setup")
            self.assertEqual(res.status_code, 200)
            self.assertIn("text/html", res.headers.get("content-type", ""))
            self.assertIn("Nuxiva OS", res.text)

    def test_mark_done_synchronizes_activation(self):
        setup_api._mark_done("test_source")
        setup_file = self.state_dir / "setup.json"
        act_file = self.state_dir / "activation.json"
        self.assertTrue(setup_file.exists())
        self.assertTrue(act_file.exists())
        setup_data = json.loads(setup_file.read_text(encoding="utf-8"))
        act_data = json.loads(act_file.read_text(encoding="utf-8"))
        self.assertTrue(setup_data.get("done"))
        self.assertEqual(act_data.get("stage"), "done")


if __name__ == "__main__":
    unittest.main()
