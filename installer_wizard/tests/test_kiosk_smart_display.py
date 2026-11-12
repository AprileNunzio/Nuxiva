import unittest
from pathlib import Path
from unittest.mock import AsyncMock, mock_open, patch

from features.desktop.screens import has_physical_screen
from health import kiosk_check, mic_check


class TestKioskSmartDisplay(unittest.IsolatedAsyncioTestCase):
    def test_has_physical_screen_connected(self):
        with patch("os.environ.get", return_value="0"), \
             patch("glob.glob", return_value=["/sys/class/drm/card0-HDMI-A-1/status"]), \
             patch("builtins.open", mock_open(read_data="connected\n")):
            self.assertTrue(has_physical_screen())

    def test_has_physical_screen_disconnected(self):
        with patch("os.environ.get", return_value="0"), \
             patch("glob.glob", return_value=["/sys/class/drm/card0-HDMI-A-1/status", "/sys/class/drm/card0-DP-1/status"]), \
             patch("builtins.open", mock_open(read_data="disconnected\n")):
            self.assertFalse(has_physical_screen())

    def test_has_physical_screen_force_override(self):
        with patch.dict("os.environ", {"NUXIVA_KIOSK_FORCE": "1"}):
            self.assertTrue(has_physical_screen())

    def test_has_physical_screen_framebuffer_fallback(self):
        with patch("os.environ.get", return_value="0"), \
             patch("glob.glob", return_value=[]), \
             patch("os.path.exists", side_effect=lambda p: p == "/dev/fb0"):
            self.assertTrue(has_physical_screen())

    async def test_kiosk_check_headless_standby_returns_ok(self):
        with patch("features.desktop.screens.has_physical_screen", return_value=False):
            res = await kiosk_check()
            self.assertEqual(res["status"], "ok")
            self.assertTrue(res.get("headless"))
            self.assertIn("Standby", res["detail"])
            self.assertIn("memoria risparmiata", res["detail"])

    async def test_kiosk_check_screen_present_no_windows_warns(self):
        with patch("features.desktop.screens.has_physical_screen", return_value=True), \
             patch("health.sh", AsyncMock(return_value=(0, ""))):
            res = await kiosk_check()
            self.assertEqual(res["status"], "warn")
            self.assertIn("Sessione grafica assente", res["detail"])

    async def test_kiosk_check_screen_present_with_chromium_ok(self):
        proc_out = "chromium --kiosk --user-data-dir=/home/kiosk/.config/nuxiva-chromium http://127.0.0.1/"
        with patch("features.desktop.screens.has_physical_screen", return_value=True), \
             patch("health.sh", AsyncMock(return_value=(0, proc_out))):
            res = await kiosk_check()
            self.assertEqual(res["status"], "ok")
            self.assertIn("Chromium attivo", res["detail"])

    def test_mic_check_ignores_headless(self):
        with patch("features.desktop.screens.has_physical_screen", return_value=False):
            self.assertIsNone(mic_check({"NUXIVA_KIOSK": "1"}))

    def test_launch_script_structure(self):
        root = Path(__file__).resolve().parents[2]
        launch = root / "scripts" / "os" / "kiosk" / "launch.sh"
        self.assertTrue(launch.is_file())
        content = launch.read_text(encoding="utf-8")
        self.assertIn("has_connected_screen()", content)
        self.assertIn("clean_stale_x_locks()", content)
        self.assertIn("/sys/class/drm/card*-*/status", content)
        self.assertIn("kiosk in standby per risparmiare memoria", content)
        self.assertIn("Pulizia lock X0 orfano", content)

    def test_session_script_structure(self):
        root = Path(__file__).resolve().parents[2]
        session = root / "scripts" / "os" / "kiosk" / "session.sh"
        self.assertTrue(session.is_file())
        content = session.read_text(encoding="utf-8")
        self.assertIn("server_responding()", content)
        self.assertIn("SingletonLock", content)
        self.assertIn("Nessuno schermo collegato rilevato", content)


if __name__ == "__main__":
    unittest.main()
