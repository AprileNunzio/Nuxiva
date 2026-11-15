import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from permissions import policy as policy_module
from permissions.catalog import BY_KEY, Level
from permissions.gate import Answer, Denied, Gate, Request
from settings import paths


class PolicyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.file = root / "permissions.json"
        self.patches = [mock.patch.object(paths, "KEY_FILE", root / "integrity.key"),
                        mock.patch.object(paths, "DATA_DIR", root)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_risky_capabilities_start_by_asking_and_outside_folders_are_denied(self):
        policy = policy_module.Policy(self.file)
        for key in ("shell.powershell", "scripts.run", "remote.ssh"):
            self.assertIs(policy.level(key), Level.ASK, key)
        self.assertIs(policy.level("files.outside"), Level.DENY)
        self.assertTrue(BY_KEY["shell.powershell"].risky)

    def test_everyday_capabilities_are_allowed_by_default(self):
        policy = policy_module.Policy(self.file)
        for key in ("files.modify", "desktop.control", "senses.webcam", "senses.microphone", "compute.ollama", "research.web"):
            self.assertIs(policy.level(key), Level.ALLOW, key)

    def test_a_legacy_file_lifts_old_default_questions_but_keeps_explicit_choices(self):
        policy = policy_module.Policy(self.file)
        levels = {k: v.value for k, v in policy.levels.items()}
        levels.update({"files.modify": "ask", "senses.webcam": "deny", "desktop.control": "ask"})
        legacy = {"levels": levels, "folders": [], "mac": policy._mac(levels, [])}
        self.file.write_text(json.dumps(legacy), encoding="utf-8")
        migrated = policy_module.Policy(self.file)
        self.assertFalse(migrated.tampered)
        self.assertIs(migrated.level("files.modify"), Level.ALLOW)
        self.assertIs(migrated.level("desktop.control"), Level.ALLOW)
        self.assertIs(migrated.level("senses.webcam"), Level.DENY)
        self.assertEqual(json.loads(self.file.read_text(encoding="utf-8"))["v"], 2)

    def test_a_forged_version_is_treated_as_tampered(self):
        policy_module.Policy(self.file)
        data = json.loads(self.file.read_text(encoding="utf-8"))
        data["v"] = 1
        self.file.write_text(json.dumps(data), encoding="utf-8")
        self.assertTrue(policy_module.Policy(self.file).tampered)

    def test_choices_persist_and_are_signed(self):
        policy_module.Policy(self.file).set("shell.powershell", Level.ALLOW)
        again = policy_module.Policy(self.file)
        self.assertIs(again.level("shell.powershell"), Level.ALLOW)
        self.assertFalse(again.tampered)

    def test_editing_the_file_outside_nuxiva_restores_safe_values(self):
        policy_module.Policy(self.file)
        data = json.loads(self.file.read_text(encoding="utf-8"))
        data["levels"]["shell.powershell"] = "allow"
        self.file.write_text(json.dumps(data), encoding="utf-8")
        tampered = policy_module.Policy(self.file)
        self.assertTrue(tampered.tampered)
        self.assertIs(tampered.level("shell.powershell"), Level.ASK)

    def test_a_corrupt_file_is_treated_as_tampered(self):
        self.file.write_text("{non json", encoding="utf-8")
        self.assertTrue(policy_module.Policy(self.file).tampered)

    def test_only_existing_absolute_folders_can_be_added(self):
        policy = policy_module.Policy(self.file)
        policy.set_folders([self.tmp.name])
        self.assertEqual(policy.folders, [str(Path(self.tmp.name).resolve())])
        for bad in ("relativa", str(Path(self.tmp.name) / "manca")):
            with self.assertRaises(ValueError):
                policy.set_folders([bad])


class GateTest(PolicyTest):
    def gate(self, answer: Answer):
        policy = policy_module.Policy(self.file)
        asked = []
        return Gate(policy, lambda capability, request: asked.append(request) or answer), policy, asked

    def test_allow_runs_without_asking(self):
        gate, _policy, asked = self.gate(Answer(False))
        gate.check(Request("files.create", "Creare un file"))
        self.assertEqual(asked, [])

    def test_never_is_refused_without_asking(self):
        gate, _policy, asked = self.gate(Answer(True))
        with self.assertRaises(Denied):
            gate.check(Request("files.outside", "Scrivere in C:/Windows"))
        self.assertEqual(asked, [])

    def test_ask_shows_the_exact_request_and_can_remember(self):
        gate, policy, asked = self.gate(Answer(True, remember=True))
        gate.check(Request("shell.powershell", "Eseguire un comando PowerShell", "Get-Process"))
        self.assertEqual(asked[0].detail, "Get-Process")
        self.assertIs(policy.level("shell.powershell"), Level.ALLOW)

    def test_a_refusal_raises(self):
        gate, policy, _asked = self.gate(Answer(False))
        with self.assertRaises(Denied):
            gate.check(Request("remote.ssh", "ssh"))
        self.assertIs(policy.level("remote.ssh"), Level.ASK)


if __name__ == "__main__":
    unittest.main()
