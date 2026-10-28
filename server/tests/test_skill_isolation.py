import signal
import subprocess
import sys
import unittest
from pathlib import Path

from server.core.skill_forge import isolation
from server.core.skill_forge.sandbox import isolation_report, run_isolated

PROBE = (
    "import importlib.util,sys,ctypes\n"
    "spec=importlib.util.spec_from_file_location('iso',sys.argv[1])\n"
    "mod=importlib.util.module_from_spec(spec)\n"
    "spec.loader.exec_module(mod)\n"
    "state=mod.apply()\n"
    "sys.stdout.write(repr(state)+'\\n')\n"
    "sys.stdout.flush()\n"
    "if not state['seccomp']:\n"
    "    sys.exit(77)\n"
    "ctypes.CDLL(None,use_errno=True).socket(2,1,0)\n"
    "sys.exit(0)\n"
)
PATH = str(Path(isolation.__file__))


class FilterProgramTest(unittest.TestCase):
    def test_every_architecture_builds_a_consistent_program(self):
        for machine in isolation.ARCHITECTURES:
            with self.subTest(machine=machine):
                steps = isolation.program(machine)
                kill = len(steps) - 1
                self.assertEqual(steps[-1][3], isolation.RET_KILL)
                self.assertEqual(steps[-2][3], isolation.RET_ALLOW)
                for index, (code, jump_true, jump_false, value) in enumerate(steps):
                    if code in (isolation.BPF_JEQ_K, isolation.BPF_JGE_K):
                        self.assertLessEqual(index + 1 + jump_true, kill)
                        self.assertLessEqual(jump_true, 255)
                denied = [step[3] for step in steps[4:-2] if step[0] == isolation.BPF_JEQ_K]
                self.assertEqual(sorted(denied), sorted(isolation.DENIED[machine]))

    def test_dangerous_calls_are_denied_on_every_architecture(self):
        names = {"x86_64": {41: "socket", 42: "connect", 59: "execve", 101: "ptrace", 272: "unshare", 165: "mount"},
                 "aarch64": {198: "socket", 203: "connect", 221: "execve", 117: "ptrace", 97: "unshare", 40: "mount"}}
        for machine, table in names.items():
            for number, name in table.items():
                with self.subTest(machine=machine, call=name):
                    self.assertIn(number, isolation.DENIED[machine])

    def test_unknown_architecture_is_reported_not_guessed(self):
        self.assertFalse(isolation._seccomp(None, "riscv64"))


class LiveIsolationTest(unittest.TestCase):
    def test_a_forbidden_call_terminates_the_process(self):
        done = subprocess.run([sys.executable, "-I", "-S", "-c", PROBE, PATH], capture_output=True, timeout=10, check=False)
        if done.returncode == 77:
            self.skipTest("seccomp is not permitted on this host")
        self.assertEqual(done.returncode, -getattr(signal, "SIGSYS", 31))

    def test_network_namespace_leaves_no_usable_interface(self):
        code = (
            "import importlib.util,sys,socket\n"
            "spec=importlib.util.spec_from_file_location('iso',sys.argv[1])\n"
            "mod=importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(mod)\n"
            "state=mod.apply()\n"
            "if not state['namespaces']:\n"
            "    sys.exit(77)\n"
            "sys.stdout.write(','.join(sorted(n for _, n in socket.if_nameindex())))\n"
        )
        done = subprocess.run([sys.executable, "-I", "-S", "-c", code, PATH], capture_output=True, timeout=10, check=False)
        if done.returncode == 77:
            self.skipTest("namespaces are not permitted on this host")
        self.assertIn(done.stdout.decode().strip(), ("", "lo"))


class SandboxReportTest(unittest.TestCase):
    def test_normal_skill_runs_and_isolation_is_reported_honestly(self):
        outcome = run_isolated("def run(slots):\n    return {'speech': 'ciao ' + slots['name']}\n", {"name": "Anna"})
        self.assertTrue(outcome.is_ok)
        self.assertEqual(outcome.value["speech"], "ciao Anna")
        report = isolation_report()
        self.assertTrue(report["observed"])
        self.assertEqual(set(report["layers"]), set(("namespaces", "no_new_privs", "seccomp")))
        self.assertEqual(report["complete"], not report["degraded"])


if __name__ == "__main__":
    unittest.main()
