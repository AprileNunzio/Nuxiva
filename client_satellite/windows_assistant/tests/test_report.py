import unittest

from app import report
from i18n.strings import t


class ReportTest(unittest.TestCase):
    def test_reply_survives_when_every_action_succeeded(self):
        self.assertEqual(report.compose("Fatto, signore.", [{"type": "create_folder", "ok": True}]), "Fatto, signore.")

    def test_failed_actions_override_a_claimed_success(self):
        out = report.compose("Ho aperto il sito.", [{"type": "open_url", "ok": False, "error": "non autorizzato"}])
        self.assertEqual(out, t("report.failed", detail="non autorizzato"))

    def test_partial_failure_is_reported(self):
        out = report.compose("Tutto fatto.", [{"type": "create_folder", "ok": True},
                                              {"type": "create_file", "ok": False, "error": "disco pieno"}])
        self.assertEqual(out, t("report.partial", done=1, failed=1, detail="disco pieno"))

    def test_site_report_names_the_real_browser(self):
        opened = {"type": "open_url", "ok": True, "url": "https://nunziotech.com", "browser": "Google Chrome"}
        self.assertEqual(report.compose("", [opened]),
                         t("report.site_opened_in", url="https://nunziotech.com", browser="Google Chrome"))

    def test_browser_fallback_is_never_hidden_by_the_model_reply(self):
        fallback = {"type": "open_url", "ok": True, "url": "https://nunziotech.com", "browser": "", "fallback": True,
                    "requested_browser": "Google Chrome"}
        self.assertEqual(report.compose("Aperto in Chrome.", [fallback]),
                         t("report.site_fallback", url="https://nunziotech.com", browser="Google Chrome"))

    def test_no_actions_keeps_the_reply(self):
        self.assertEqual(report.compose("Ciao!", []), "Ciao!")

    def test_error_codes_are_translated(self):
        self.assertEqual(report.error_message("brain_unavailable"), t("brain.unavailable"))
        self.assertEqual(report.error_message("privacy_blocked"), t("brain.privacy_blocked"))
        self.assertEqual(report.error_message("???"), t("brain.failed"))
        self.assertNotEqual(t("brain.unavailable"), "brain.unavailable")


if __name__ == "__main__":
    unittest.main()
