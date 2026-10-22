import asyncio
import shutil
import subprocess
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from features.devstudio import publish, runner, starters, tools, workspace
from features.devstudio.workspace import DevError


def can_isolate() -> bool:
    if not shutil.which("unshare"):
        return False
    return subprocess.run(["unshare", "--net", "--", "true"], capture_output=True).returncode == 0


class DevCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "progetti"
        self.sites = Path(self.tmp.name) / "siti"
        self.patches = [unittest.mock.patch.object(workspace, "ROOT", self.root),
                        unittest.mock.patch.object(publish.archive, "folder", lambda kind: self.sites),
                        unittest.mock.patch.object(publish, "my_ip", lambda: "10.0.0.2")]
        for patch in self.patches:
            patch.start()
        self.sites.mkdir()

    def tearDown(self):
        for patch in self.patches:
            patch.stop()
        self.tmp.cleanup()

    def call(self, fn, *args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))


class WorkspaceTest(DevCase):
    def project(self):
        folder = workspace.project_dir("demo", must_exist=False)
        folder.mkdir(parents=True)
        return folder

    def test_paths_cannot_escape_the_project(self):
        folder = self.project()
        for bad in ("../x.py", "a/../../x", "", ".", "a b.py", "x" * 70, "/".join(["d"] * 12) + "/f.py"):
            with self.subTest(path=bad), self.assertRaises(DevError):
                workspace.safe_path(folder, bad)

    def test_absolute_paths_stay_inside_the_project(self):
        folder = self.project()
        target = workspace.safe_path(folder, "/etc/passwd")
        self.assertTrue(target.resolve().is_relative_to(folder.resolve()))

    def test_symlinks_are_refused(self):
        folder = self.project()
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir()
        (folder / "link").symlink_to(outside)
        with self.assertRaises(DevError):
            workspace.write(folder, "link/evil.py", "x")
        self.assertFalse((outside / "evil.py").exists())

    def test_limits_are_enforced(self):
        folder = self.project()
        with self.assertRaises(DevError):
            workspace.write(folder, "big.txt", "x" * (workspace.MAX_FILE + 1))
        with unittest.mock.patch.object(workspace, "MAX_FILES", 2):
            workspace.write(folder, "a.txt", "1")
            workspace.write(folder, "b.txt", "1")
            with self.assertRaises(DevError):
                workspace.write(folder, "c.txt", "1")
            workspace.write(folder, "a.txt", "2")

    def test_names_are_validated(self):
        for bad in ("../x", "9abc", "a", ""):
            with self.subTest(name=bad), self.assertRaises(DevError):
                workspace.slug(bad)
        self.assertEqual(workspace.slug("Mio Sito"), "mio-sito")


class StarterTest(DevCase):
    def test_every_kind_scaffolds_valid_files(self):
        for kind in starters.KINDS:
            with self.subTest(kind=kind):
                reply = self.call(tools.dev_new, f"prova-{kind.replace('_', '-')}", kind)
                self.assertIn("creato", reply)

    def test_unknown_kind_and_duplicates_are_refused(self):
        self.assertTrue(self.call(tools.dev_new, "uno", "cobol").startswith("ERRORE"))
        self.call(tools.dev_new, "uno", "static_site")
        self.assertIn("esiste già", self.call(tools.dev_new, "uno", "static_site"))

    def test_write_read_tree_roundtrip(self):
        self.call(tools.dev_new, "app", "python_cli")
        self.assertIn("scritto", self.call(tools.dev_write, "app", "extra/util.py", "VALUE = 1\n"))
        self.assertEqual(self.call(tools.dev_read, "app", "extra/util.py"), "VALUE = 1\n")
        self.assertIn("extra/util.py", self.call(tools.dev_tree, "app"))
        self.assertTrue(self.call(tools.dev_write, "app", "../x.py", "x").startswith("ERRORE"))
        self.assertIn("app", self.call(tools.dev_tree))


class RunnerTest(DevCase):
    def test_unknown_checks_and_entries_are_refused(self):
        self.call(tools.dev_new, "app", "python_cli")
        folder = workspace.project_dir("app")
        with self.assertRaises(DevError):
            runner.command("rm_all", folder, "")
        with self.assertRaises(DevError):
            runner.command("python_run", folder, "main.js")
        with self.assertRaises(DevError):
            runner.command("python_run", folder, "../main.py")

    def test_refuses_without_network_isolation(self):
        self.call(tools.dev_new, "app", "python_cli")
        with unittest.mock.patch.object(runner.shutil, "which", side_effect=lambda n: "/usr/bin/python3" if n == "python3" else None):
            self.assertIn("isolamento", self.call(tools.dev_run, "app", "python_tests"))

    def test_environment_is_scrubbed(self):
        env = runner.environment(Path("/tmp/x"))
        self.assertNotIn("NUXIVA_SECRET_KEY", env)
        self.assertEqual(set(env) & {"HOME", "PATH"}, {"HOME", "PATH"})

    def test_tool_requires_confirmation(self):
        from features.agent import registry
        self.assertTrue(registry.TOOLS["dev_run"]["confirm"])

    @unittest.skipUnless(can_isolate(), "unshare --net non disponibile")
    def test_generated_python_project_passes_its_own_tests(self):
        self.call(tools.dev_new, "app", "python_cli")
        reply = self.call(tools.dev_run, "app", "python_tests")
        self.assertIn("riuscito", reply, reply)

    @unittest.skipUnless(can_isolate(), "unshare --net non disponibile")
    def test_failing_code_is_reported_as_failed(self):
        self.call(tools.dev_new, "app", "python_cli")
        self.call(tools.dev_write, "app", "test_bad.py", "import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n        self.assertEqual(1, 2)\n")
        self.assertIn("fallito", self.call(tools.dev_run, "app", "python_tests"))

    @unittest.skipUnless(can_isolate(), "unshare --net non disponibile")
    def test_code_has_no_network(self):
        self.call(tools.dev_new, "app", "python_cli")
        code = "import socket\ns=socket.socket()\ns.settimeout(2)\ntry:\n    s.connect(('93.184.216.34',80))\n    print('CONNECTED')\nexcept OSError:\n    print('BLOCKED')\n"
        self.call(tools.dev_write, "app", "net.py", code)
        reply = self.call(tools.dev_run, "app", "python_run", "net.py")
        self.assertIn("BLOCKED", reply)
        self.assertNotIn("CONNECTED", reply)


class PublishTest(DevCase):
    def test_static_site_is_published(self):
        self.call(tools.dev_new, "vetrina", "static_site")
        self.call(tools.dev_write, "vetrina", "secret.py", "x")
        reply = self.call(tools.dev_publish, "vetrina")
        self.assertIn("http://10.0.0.2/siti/vetrina/", reply)
        self.assertTrue((self.sites / "vetrina" / "index.html").is_file())
        self.assertFalse((self.sites / "vetrina" / "secret.py").exists())

    def test_project_without_index_is_not_published(self):
        self.call(tools.dev_new, "api", "fastapi_service")
        self.assertTrue(self.call(tools.dev_publish, "api").startswith("ERRORE"))


if __name__ == "__main__":
    unittest.main()
