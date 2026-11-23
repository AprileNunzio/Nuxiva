import unittest
from unittest import mock

from actions import launch
from actions.common import ActionError
from i18n.strings import t


class Gate:
    def __init__(self):
        self.summaries = []

    def check(self, request, always_ask=False):
        self.summaries.append(request.summary)


class OpenUrlTest(unittest.TestCase):
    def launcher(self, apps):
        return launch.Launcher(Gate(), mock.Mock(), apps)

    def test_named_browser_is_used_when_installed(self):
        launcher = self.launcher({"Google Chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe"})
        with mock.patch.object(launch, "shell_open") as shell, mock.patch.object(launch.webbrowser, "open") as default:
            outcome = launcher.open_url({"url": "https://nunziotech.com", "browser": "chrome"})
        shell.assert_called_once_with(r"C:\Program Files\Google\Chrome\Application\chrome.exe", '"https://nunziotech.com"')
        default.assert_not_called()
        self.assertEqual(outcome.data, {"url": "https://nunziotech.com", "browser": "Google Chrome"})
        self.assertIn("Google Chrome", launcher.gate.summaries[0])

    def test_missing_browser_falls_back_and_says_so(self):
        launcher = self.launcher({})
        with mock.patch.object(launch, "shell_open") as shell, \
                mock.patch.object(launch.webbrowser, "open", return_value=True) as default:
            outcome = launcher.open_url({"url": "https://nunziotech.com", "browser": "chrome"})
        shell.assert_not_called()
        default.assert_called_once_with("https://nunziotech.com")
        self.assertTrue(outcome.data["fallback"])
        self.assertEqual(outcome.data["requested_browser"], "Google Chrome")

    def test_failed_default_open_is_an_error(self):
        with mock.patch.object(launch.webbrowser, "open", return_value=False):
            with self.assertRaises(ActionError):
                self.launcher({}).open_url({"url": "https://nunziotech.com"})

    def test_unsafe_urls_and_unknown_browsers_are_refused(self):
        launcher = self.launcher({})
        for action in ({"url": "javascript:alert(1)"}, {"url": 'https://a.com/" --x'},
                       {"url": "https://a.com", "browser": "cmd.exe"}):
            with self.assertRaises(ActionError):
                launcher.open_url(action)
        self.assertEqual(launcher.gate.summaries, [])
        self.assertNotEqual(t("web.only_http"), "web.only_http")


if __name__ == "__main__":
    unittest.main()
