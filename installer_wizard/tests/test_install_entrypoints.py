import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO = "AprileNunzio/Nuxiva"
URL = re.compile(r"https://(?:raw\.githubusercontent\.com|github\.com)/([^/\s]+/[^/\s.]+)")


class InstallEntryPointsTest(unittest.TestCase):
    def test_readmes_point_to_the_live_repository(self):
        for name in ("README.md", "README_IT.md", "README_FR.md", "README_ES.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            install = [line for line in text.splitlines() if "install.sh" in line and ("curl" in line or "wget" in line)]
            self.assertTrue(install, name)
            self.assertTrue(any(line.endswith("/main/install.sh | sudo bash") for line in install), name)
            for line in install:
                self.assertIn(f"https://raw.githubusercontent.com/{REPO}/main/install.sh", line, name)
            for found in URL.findall(text):
                if found.lower().endswith("/nuxiva"):
                    self.assertEqual(found.lower(), REPO.lower(), name)

    def test_scripts_use_the_live_repository(self):
        for path in (ROOT / "install.sh", ROOT / "installer_wizard" / "bootstrap.sh"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("aprilenunzio88", text.lower())
            self.assertIn(REPO, text)

    def test_bootstrap_elevates_instead_of_aborting_when_piped(self):
        text = (ROOT / "installer_wizard" / "bootstrap.sh").read_text(encoding="utf-8")
        block = text[text.index('if [ "$EUID" -ne 0 ]'):text.index("command -v apt-get")]
        self.assertNotIn("[ ! -t 0 ]", block)
        self.assertIn("exec sudo env", block)
        self.assertIn("</dev/tty", block)
        self.assertEqual(text.count("[sudo]="), 2)

    def test_remote_install_is_pinned_and_verified_before_running(self):
        text = (ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn("raw.githubusercontent.com/$SLUG/$REF/", text)
        self.assertIn("api.github.com/repos/$SLUG/contents/$path?ref=$REF", text)
        self.assertIn("blob_sha1", text)
        fetch = text.index('fetch_verified installer_wizard/bootstrap.sh')
        run = text.index('bash "$WORK/bootstrap.sh"')
        self.assertLess(fetch, run)
        self.assertNotIn("| bash", text)

    def test_uninstall_is_available(self):
        self.assertTrue((ROOT / "scripts" / "os" / "uninstall.sh").is_file())
        ctl = (ROOT / "scripts" / "os" / "nuxivactl").read_text(encoding="utf-8")
        self.assertIn("uninstall|remove)", ctl)
        boot = (ROOT / "installer_wizard" / "bootstrap.sh").read_text(encoding="utf-8")
        self.assertIn('reset --hard --quiet "$PIN_REF"', boot)


if __name__ == "__main__":
    unittest.main()
