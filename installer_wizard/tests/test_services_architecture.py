import unittest

from features.services.command_center import command_center
from features.services.download_manager import DownloadManager
from features.services.install_manager import InstallManager


class TestServicesArchitecture(unittest.IsolatedAsyncioTestCase):
    async def test_download_manager_rejects_unsafe_urls(self):
        dm = DownloadManager()
        with self.assertRaises(ValueError):
            dm._sanitize_url("ftp://example.com/file.bin")
        with self.assertRaises(ValueError):
            dm._sanitize_url("file:///etc/passwd")
        with self.assertRaises(ValueError):
            dm._sanitize_url("javascript:alert(1)")
        self.assertEqual(dm._sanitize_url("https://example.com/model.bin"), "https://example.com/model.bin")

    async def test_download_manager_cancel(self):
        dm = DownloadManager()
        task_id = "test_1"
        from pathlib import Path
        from features.services.download_manager import DownloadTask
        task = DownloadTask(id=task_id, url="https://example.com/test", destination=Path("/tmp/test"), status="downloading")
        dm._tasks[task_id] = task
        self.assertTrue(dm.cancel(task_id))
        self.assertEqual(task.status, "cancelled")
        self.assertTrue(task.cancelled)

    async def test_install_manager_wanted_background_steps(self):
        im = InstallManager()
        env = {
            "NUXIVA_BRAIN": "local",
            "NUXIVA_VISION": "0",
            "NUXIVA_EAR": "0",
            "NUXIVA_VOICE_PACKAGE": "0",
            "NUXIVA_DOCUMENTS": "0",
            "NUXIVA_STUDY_FINETUNE": "0",
        }
        steps = im.wanted_background_steps(env)
        step_ids = {s.id for s in steps}
        self.assertNotIn("soup", step_ids)
        self.assertNotIn("vision", step_ids)
        self.assertNotIn("ear", step_ids)

    async def test_command_center_overview(self):
        ov = command_center.overview()
        self.assertIn("downloads", ov)
        self.assertIn("installs", ov)
        self.assertIn("notifications", ov)
        self.assertIn("updates", ov)


if __name__ == "__main__":
    unittest.main()
