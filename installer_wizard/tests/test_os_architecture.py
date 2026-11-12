import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from agenti.os.api import routes
from agenti.os.taskbar_manager import TaskbarManager
from agenti.os.wallpaper_manager import WallpaperManager
from agenti.os.window_manager import WindowManager


class TestOSArchitecture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_window_manager_lifecycle(self):
        wm = WindowManager(self.tmp_path / "win.json")
        win = wm.register_window("win_1", "Test Window", "chat", 640, 480, 50, 50)
        self.assertEqual(win["id"], "win_1")
        self.assertEqual(win["title"], "Test Window")
        self.assertEqual(win["state"], "normal")

        self.assertTrue(wm.update_state("win_1", "maximized"))
        windows = wm.get_windows()
        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0]["state"], "maximized")

        self.assertTrue(wm.update_geometry("win_1", 100, 100, 800, 600))
        self.assertEqual(wm.get_windows()[0]["width"], 800)

        self.assertTrue(wm.close_window("win_1"))
        self.assertEqual(len(wm.get_windows()), 0)

    def test_window_manager_rejects_invalid_id(self):
        wm = WindowManager(self.tmp_path / "win.json")
        with self.assertRaises(ValueError):
            wm.register_window("../../../etc/passwd", "Bad Window", "app")

    def test_wallpaper_manager(self):
        wpm = WallpaperManager(self.tmp_path / "wp.json")
        wp = wpm.get_wallpaper()
        self.assertIn("mode", wp)
        self.assertIn("available_modes", wp)

        updated = wpm.set_wallpaper("deep_space", "default", True)
        self.assertEqual(updated["mode"], "deep_space")
        self.assertTrue(updated["blur"])

        with self.assertRaises(ValueError):
            wpm.set_wallpaper("invalid_mode")

    def test_taskbar_manager(self):
        tbm = TaskbarManager(self.tmp_path / "tb.json")
        pinned = tbm.get_pinned_apps()
        self.assertGreaterEqual(len(pinned), 1)

        self.assertTrue(tbm.pin_app("notes", "app_notes", "notepad"))
        self.assertTrue(any(item["app_id"] == "notes" for item in tbm.get_pinned_apps()))

        self.assertTrue(tbm.unpin_app("notes"))
        self.assertFalse(any(item["app_id"] == "notes" for item in tbm.get_pinned_apps()))

    def test_os_api_routes(self):
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(routes)
        client = TestClient(app)

        resp = client.get("/api/os/windows")
        self.assertEqual(resp.status_code, 200)

        resp = client.get("/api/os/wallpaper")
        self.assertEqual(resp.status_code, 200)

        resp = client.get("/api/os/taskbar")
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
