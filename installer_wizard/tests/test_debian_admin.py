import asyncio
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from features.agent import registry
from features.experts import admin, store, templates, tools


def run(coro):
    return asyncio.run(coro)


class AdminTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        for patch in (mock.patch.object(admin, "AUDIT", root / "audit.log"), mock.patch.object(admin, "SSH_DIR", root / "ssh"),
                      mock.patch.object(admin.store, "event")):
            patch.start()
            self.addCleanup(patch.stop)
        self.root = root

    def test_package_validation(self):
        self.assertEqual(admin.packages("htop, curl  vim=2:9.0"), ["htop", "curl", "vim=2:9.0"])
        for bad in ("", "-y", "a;b", "$(x)", " ".join(["p"] * 31), "../x"):
            with self.assertRaises(ValueError):
                admin.packages(bad)

    def test_service_and_power_validation(self):
        admin.check_service({"unit": "ssh", "action": "enable --now"})
        for args in ({"unit": "-x", "action": "start"}, {"unit": "a b", "action": "start"}, {"unit": "ssh", "action": "explode"}):
            with self.assertRaises(ValueError):
                admin.check_service(args)
        with self.assertRaises(ValueError):
            admin.check_power({"action": "format"})

    def test_ssh_validation(self):
        admin.check_ssh({"host": "192.168.1.5", "command": "uptime"})
        for args in ({"host": "-oProxyCommand=x", "command": "a"}, {"host": "h;x", "command": "a"}, {"host": "h", "command": "  "},
                     {"host": "h", "command": "a", "user": "Root; x"}, {"host": "h", "command": "a", "port": 70000}):
            with self.assertRaises(ValueError):
                admin.check_ssh(args)

    def test_path_validation(self):
        admin.check_path({"path": "/etc/hosts"})
        for bad in ("etc/hosts", "/etc/../shadow", "/etc/a\0b", ""):
            with self.assertRaises(ValueError):
                admin.check_path({"path": bad})

    def test_run_captures_exit_code_output_and_timeout(self):
        self.assertEqual(run(admin.run(["echo", "ciao"])), "codice di uscita 0\nciao")
        self.assertIn("codice di uscita 3", run(admin.run(["bash", "-c", "echo no; exit 3"])))
        self.assertIn("codice di uscita 127", run(admin.run(["nuxiva-comando-inesistente"])))
        self.assertIn("codice di uscita 124", run(admin.run(["sleep", "5"], timeout=0.2)))

    def test_run_uses_noninteractive_environment(self):
        self.assertIn("noninteractive", run(admin.run(["bash", "-c", "echo $DEBIAN_FRONTEND"])))

    def test_audit_is_private_capped_and_recorded(self):
        admin.audit("shell", "rm -rf /tmp/x")
        self.assertIn("rm -rf", admin.AUDIT.read_text())
        self.assertEqual(stat.S_IMODE(admin.AUDIT.stat().st_mode), 0o600)
        admin.AUDIT.write_text("x" * (admin.AUDIT_CAP + 1))
        admin.audit("shell", "next")
        self.assertTrue(admin.AUDIT.with_suffix(".log.1").exists())
        admin.store.event.assert_called()

    def test_apt_install_builds_noninteractive_command(self):
        with mock.patch.object(admin, "run", mock.AsyncMock(return_value="ok")) as fake:
            run(admin.apt_install("htop curl"))
            run(admin.apt_install("htop", remove=True, purge=True))
        first, second = fake.await_args_list[0].args[0], fake.await_args_list[1].args[0]
        self.assertEqual(first[:2], ["apt-get", "-y"])
        self.assertEqual(first[-3:], ["--", "htop", "curl"])
        self.assertIn("purge", second)

    def test_apt_maintain_rejects_unknown_actions(self):
        with self.assertRaises(ValueError):
            run(admin.apt_maintain("dist-upgrade; reboot"))
        with mock.patch.object(admin, "run", mock.AsyncMock(return_value="ok")) as fake:
            run(admin.apt_maintain("full-upgrade"))
        self.assertIn("full-upgrade", fake.await_args.args[0])

    def test_power_schedules_with_grace_and_can_cancel(self):
        with mock.patch.object(admin, "run", mock.AsyncMock(return_value="ok")) as fake:
            run(admin.power("reboot", 0))
            run(admin.power("poweroff", 9999))
            run(admin.power("cancel"))
        calls = [c.args[0] for c in fake.await_args_list]
        self.assertEqual(calls[0][:3], ["shutdown", "-r", "+1"])
        self.assertEqual(calls[1][:3], ["shutdown", "-P", "+1440"])
        self.assertEqual(calls[2], ["shutdown", "-c"])

    def test_ssh_command_is_hardened_and_uses_private_key(self):
        with mock.patch.object(admin, "ssh_key", return_value=self.root / "ssh" / "id_ed25519"), \
                mock.patch.object(admin.shutil, "which", return_value="/usr/bin/ssh"), \
                mock.patch.object(admin, "run", mock.AsyncMock(return_value="ok")) as fake:
            run(admin.ssh("10.0.0.2", "uptime", "pi", 2222, 99999))
        cmd = fake.await_args.args[0]
        self.assertIn("BatchMode=yes", cmd)
        self.assertIn("2222", cmd)
        self.assertEqual(cmd[-3:], ["--", "10.0.0.2", "uptime"])
        self.assertEqual(fake.await_args.kwargs["timeout"], 1800)
        self.assertIn("pi", cmd)

    def test_shell_runs_bash_with_clamped_timeout(self):
        with mock.patch.object(admin, "run", mock.AsyncMock(return_value="ok")) as fake:
            run(admin.shell("ls /", 1))
        self.assertEqual(fake.await_args.args[0], ["bash", "-lc", "ls /"])
        self.assertEqual(fake.await_args.kwargs["timeout"], 5)
        with self.assertRaises(ValueError):
            run(admin.shell("  "))

    def test_read_only_commands_skip_confirmation(self):
        self.assertFalse(admin.risky({"command": "df -h"}))
        self.assertTrue(admin.risky({"command": "df -h; rm -rf /x"}))
        self.assertTrue(admin.risky({"command": "apt install x"}))

    def test_write_file_keeps_backup_and_permissions(self):
        target = self.root / "app.conf"
        target.write_text("old")
        os.chmod(target, 0o640)
        message = admin.write_file(str(target), "new")
        self.assertEqual(target.read_text(), "new")
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o640)
        backups = list(self.root.glob("app.conf.nuxiva-*.bak"))
        self.assertEqual(backups[0].read_text(), "old")
        self.assertIn(backups[0].name, message)
        fresh = self.root / "sub" / "x.conf"
        admin.write_file(str(fresh), "a", "600")
        self.assertEqual(stat.S_IMODE(fresh.stat().st_mode), 0o600)
        self.assertEqual(admin.read_file(str(fresh)), "a")

    def test_kill_protects_init_and_self(self):
        for pid in (0, 1, os.getpid()):
            with self.assertRaises(ValueError):
                run(admin.kill(pid))
        with self.assertRaises(ValueError):
            run(admin.kill(4242, "SEGV"))
        with mock.patch.object(admin, "run", mock.AsyncMock(return_value="ok")) as fake:
            run(admin.kill(4242, "KILL"))
        self.assertEqual(fake.await_args.args[0], ["kill", "-KILL", "4242"])

    def test_processes_limits_rows(self):
        out = run(admin.processes("mem", 3))
        self.assertLessEqual(len(out.splitlines()), 6)


class RegistrationTest(unittest.TestCase):
    NAMES = ("apt_install", "apt_remove", "apt_maintain", "service_control", "power_control", "ssh_exec", "debian_shell",
             "system_file_write", "process_kill")

    def test_mutating_tools_require_confirmation(self):
        for name in ("apt_install", "apt_remove", "apt_maintain", "service_control", "power_control", "system_file_write", "process_kill"):
            self.assertTrue(registry.needs_confirm(name, {}), name)
        self.assertTrue(registry.needs_confirm("debian_shell", {"command": "systemctl restart x"}))
        self.assertFalse(registry.needs_confirm("debian_shell", {"command": "uptime"}))
        self.assertTrue(registry.needs_confirm("ssh_exec", {"command": "reboot"}))
        self.assertFalse(registry.needs_confirm("apt_search", {}))

    def test_prechecks_reject_bad_arguments_before_asking(self):
        self.assertIn("pacchetti", registry.precheck("apt_install", {"packages": "x;y"}))
        self.assertIn("azione", registry.precheck("power_control", {"action": "x"}))
        self.assertEqual(registry.precheck("service_control", {"unit": "ssh", "action": "restart"}), "")

    def test_all_new_tools_belong_to_the_debian_template(self):
        spec = templates.SPECS["debian"]
        for name in self.NAMES:
            self.assertIn(name, spec["tools"])
            self.assertIn(name, registry.TOOLS)
        self.assertLessEqual(len(spec["tools"]), 24)
        self.assertLessEqual(len(spec["skills"]), 12)

    def test_existing_debian_experts_gain_new_skills_and_instructions(self):
        old = {"id": "debian", "template": "debian", "skills": ["system_health"], "tools": ["debian_status"],
               "instructions": next(iter(templates.LEGACY_INSTRUCTIONS))}
        fresh = templates.upgrade(old)
        self.assertIn("remote_ssh", fresh["skills"])
        self.assertIn("ssh_exec", fresh["tools"])
        self.assertNotIn("distruttivo", fresh["instructions"])
        custom = templates.upgrade({**old, "instructions": "mie regole"})
        self.assertEqual(custom["instructions"], "mie regole")
        self.assertEqual(templates.upgrade({"template": ""}), {"template": ""})
        self.assertIs(store.templates, templates)
        self.assertTrue(callable(tools.apt_install))


if __name__ == "__main__":
    unittest.main()
