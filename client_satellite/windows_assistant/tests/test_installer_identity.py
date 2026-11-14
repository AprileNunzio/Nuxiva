import re
import unittest
from pathlib import Path
from xml.etree import ElementTree

from tests.packaging_helpers import load
from settings import agent_name
from settings.autostart import task_xml

ROOT = Path(__file__).resolve().parent.parent
NS = "{http://schemas.microsoft.com/windows/2004/02/mit/task}"


class AgentNameTest(unittest.TestCase):
    def test_names_are_sanitized_for_files_and_display(self):
        self.assertEqual(agent_name.clean("Hey  Jarvis"), "Jarvis")
        self.assertEqual(agent_name.clean('Ni<c>o:/\\"x'), "Nicox")
        self.assertEqual(agent_name.clean("A" * 80), "A" * agent_name.MAX_LENGTH)
        self.assertEqual(agent_name.clean(None), "")
        self.assertEqual(agent_name.clean("..."), "")

    def test_display_and_shortcut(self):
        self.assertEqual(agent_name.display(""), "Nuxiva")
        self.assertEqual(agent_name.display("nuxiva"), "Nuxiva")
        self.assertEqual(agent_name.display("Aria"), "Nuxiva · Aria")
        self.assertEqual(agent_name.shortcut_file("Aria"), "Aria.lnk")
        self.assertEqual(agent_name.shortcut_file("Nuxiva"), "")
        self.assertNotIn("/", agent_name.shortcut_file("a/b"))


class TaskTest(unittest.TestCase):
    def test_task_runs_elevated_without_battery_limits(self):
        body = task_xml(r"C:\Program Files\Nuxiva\Nuxiva.exe", "", r"C:\Program Files\Nuxiva", r"PC\A&B")
        root = ElementTree.fromstring(body.replace('encoding="UTF-16"', 'encoding="UTF-8"'))
        self.assertEqual(root.find(f".//{NS}RunLevel").text, "HighestAvailable")
        self.assertEqual(root.find(f".//{NS}DisallowStartIfOnBatteries").text, "false")
        self.assertEqual(root.find(f".//{NS}ExecutionTimeLimit").text, "PT0S")
        self.assertEqual(root.find(f".//{NS}Command").text, r"C:\Program Files\Nuxiva\Nuxiva.exe")
        self.assertEqual(root.find(f".//{NS}UserId").text, r"PC\A&B")


class InstallerScriptTest(unittest.TestCase):
    def setUp(self):
        self.iss = (ROOT / "packaging" / "installer.iss").read_text(encoding="utf-8")
        self.spec = (ROOT / "packaging" / "nuxiva_assistant.spec").read_text(encoding="utf-8")

    def test_installs_as_admin_into_start_menu_with_icon(self):
        for needle in ("PrivilegesRequired=admin", "{autopf}", "{autoprograms}", "{autodesktop}", "SetupIconFile=",
                       "UninstallDisplayIcon=", "AppPublisher=", "VersionInfoVersion=", "DisableFinishedPage=yes", "DisableWelcomePage=yes", "DisableReadyPage=yes", "MinVersion=10.0",
                       "AppSupportURL=", "AppUpdatesURL=", "AppCopyright="):
            self.assertIn(needle, self.iss)
        self.assertNotIn("PrivilegesRequired=lowest", self.iss)

    def test_every_name_is_nuxiva(self):
        names = re.findall(r"^(?:AppName|OutputBaseFilename|UninstallDisplayName)=(.+)$", self.iss, re.M)
        self.assertEqual(sorted(names), ["Nuxiva_Setup", "{#AppName}", "{#AppName}"])
        self.assertIn('name="Nuxiva"', self.spec)

    def test_executable_asks_for_admin_and_has_version_resource(self):
        self.assertIn("uac_admin=True", self.spec)
        self.assertIn("version_info.txt", self.spec)

    def test_old_per_user_install_is_cleaned(self):
        self.assertIn("NUXIVA Assistente.lnk", self.iss)
        self.assertIn("deletevalue", self.iss)

    def test_version_resource_is_generated(self):
        module = load("make_version")
        self.assertEqual(module.parts("5.8.0"), (5, 8, 0, 0))
        self.assertEqual(module.parts("1.2.3.4"), (1, 2, 3, 4))


if __name__ == "__main__":
    unittest.main()
