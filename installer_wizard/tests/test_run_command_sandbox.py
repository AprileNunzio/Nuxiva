import asyncio
import os
import unittest
from types import SimpleNamespace
from unittest import mock

from agenti.agent import host_readonly, shell_sandbox, tools_system
from server.features.sandbox.domain.errors import SandboxUnavailableError


def report(**kw):
    base = {"exit_code": 0, "stdout": "ok", "stderr": "", "timed_out": False, "oom_killed": False, "backend": "docker"}
    base.update(kw)
    return SimpleNamespace(**base)


class FakeGateway:
    def __init__(self, result=None, error=None):
        self.calls = []
        self.result, self.error = result or report(), error

    async def run_bash(self, source, **options):
        self.calls.append((source, options))
        if self.error:
            raise self.error
        return self.result


class ParseTest(unittest.TestCase):
    def test_plain_reads_are_allowed(self):
        for command in ("ls -la", "df -h", "uname -a", "free -m", "uptime", "ps aux", "ss -tulpn", "date +%s", "echo ciao",
                        "ip a", "ip route show", "ping -c 3 example.com", "top -bn1", "ollama list", "docker ps",
                        "systemctl status nuxiva --no-pager", "journalctl -n 50", "dpkg -l nuxiva", "apt list --upgradable",
                        "grep -r foo .", "find . -name '*.txt'", "hostnamectl", "lsb_release -a"):
            self.assertIsNotNone(host_readonly.parse(command), command)

    def test_mutating_or_unknown_commands_are_rejected(self):
        for command in ("rm -rf x", "find . -delete", "find . -exec rm {} +", "date -s 2020-01-01", "hostname evil",
                        "ip route flush all", "ip link set eth0 down", "ip addr add 1.2.3.4/24 dev eth0", "systemctl restart nuxiva",
                        "journalctl --vacuum-size=1M", "journalctl -f", "tail -f x", "docker rm x", "docker run alpine",
                        "ollama pull x", "sensors -s", "ping -c 100 host", "ping host", "top", "apt install x", "dpkg -i x.deb",
                        "curl http://x", "bash -c id", "python3 -c 1", "sudo ls", "dd if=/dev/zero of=x"):
            self.assertIsNone(host_readonly.parse(command), command)

    def test_shell_metacharacters_are_rejected(self):
        for command in ("ls; id", "ls && id", "ls | cat", "ls > x", "ls `id`", "ls $(id)", "echo $HOME", "ls\nid", "ls ~", "ls \\x"):
            self.assertIsNone(host_readonly.parse(command), command)

    def test_secret_paths_are_blocked(self):
        for command in ("cat /etc/nuxiva/nuxiva.env", "cat /etc/shadow", "ls /root", "cat /var/lib/nuxiva/x", "cat /proc/1/environ",
                        "head .env", "cat /home/a/.ssh/id_rsa", "grep -r key /etc/nuxiva", "ls " + "../" * 12 + "etc/nuxiva",
                        "wc --files0-from=/etc/shadow", "grep -f /etc/shadow x", "file -f /etc/shadow", "cat server.pem"):
            self.assertIsNone(host_readonly.parse(command), command)

    def test_limits(self):
        self.assertIsNone(host_readonly.parse("ls " + "a " * 40))
        self.assertIsNone(host_readonly.parse("ls " + "a" * 500))
        self.assertIsNone(host_readonly.parse(""))
        self.assertIsNone(host_readonly.parse("ls 'unterminated"))
        self.assertIsNone(host_readonly.parse(None))

    def test_run_has_clean_environment(self):
        with mock.patch.dict(os.environ, {"NUXIVA_SECRET_KEY": "topsecret"}):
            code, out = asyncio.run(host_readonly.run(["env"]))
        self.assertEqual(code, 0)
        self.assertNotIn("topsecret", out)
        self.assertNotIn("NUXIVA", out)

    def test_run_reports_missing_command_and_timeout(self):
        self.assertEqual(asyncio.run(host_readonly.run(["nuxiva-missing-binary"]))[0], 127)
        with mock.patch.object(host_readonly, "TIMEOUT", 0.2):
            self.assertEqual(asyncio.run(host_readonly.run(["sleep", "5"]))[0], 124)


class RunCommandTest(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, shell_sandbox, "_gateway", None)

    def run_tool(self, command, gateway=None, env=None):
        shell_sandbox._gateway = gateway
        with mock.patch.dict(os.environ, env or {}, clear=False):
            return asyncio.run(tools_system.run_command(command))

    def test_risky_command_goes_to_the_sandbox_by_default(self):
        gateway = FakeGateway(report(stdout="fatto", exit_code=3))
        text = self.run_tool("apt-get install -y x && rm file", gateway)
        self.assertEqual(len(gateway.calls), 1)
        self.assertIn("codice di uscita 3 (sandbox docker)", text)
        self.assertIn("fatto", text)

    def test_sandbox_limits_are_bounded_and_have_no_network(self):
        gateway = FakeGateway()
        self.run_tool("make build", gateway)
        limits = gateway.calls[0][1]["limits"]
        self.assertLessEqual(limits.wall_seconds, 120)
        self.assertLessEqual(limits.memory_mb, 256)
        self.assertNotIn("egress_hosts", gateway.calls[0][1])

    def test_read_only_never_touches_the_sandbox(self):
        gateway = FakeGateway()
        text = self.run_tool("echo ciao", gateway)
        self.assertEqual(gateway.calls, [])
        self.assertIn("ciao", text)

    def test_unavailable_sandbox_fails_closed(self):
        gateway = FakeGateway(error=SandboxUnavailableError("down"))
        with mock.patch.object(tools_system, "sh") as host:
            with self.assertRaises(RuntimeError):
                self.run_tool("make build", gateway)
            host.assert_not_called()

    def test_host_mode_is_explicit_opt_in(self):
        gateway = FakeGateway()
        with mock.patch.object(tools_system, "sh", return_value=(0, "dal server")) as host:
            text = self.run_tool("touch x", gateway, {"NUXIVA_RUN_COMMAND": "host"})
        host.assert_called_once()
        self.assertEqual(gateway.calls, [])
        self.assertIn("dal server", text)

    def test_unknown_mode_falls_back_to_sandbox(self):
        with mock.patch.dict(os.environ, {"NUXIVA_RUN_COMMAND": "yolo"}):
            self.assertEqual(shell_sandbox.mode(), "sandbox")

    def test_destructive_pattern_is_still_blocked(self):
        with self.assertRaises(PermissionError):
            self.run_tool("rm -rf /", FakeGateway())

    def test_timeout_and_oom_are_reported(self):
        self.assertIn("tempo scaduto", shell_sandbox.format_report(report(timed_out=True)))
        self.assertIn("memoria", shell_sandbox.format_report(report(oom_killed=True)))

    def test_confirmation_only_for_non_read_only(self):
        self.assertFalse(tools_system._risky({"command": "ls -la"}))
        self.assertTrue(tools_system._risky({"command": "touch x"}))
        self.assertTrue(tools_system._risky({"command": "find . -delete"}))
