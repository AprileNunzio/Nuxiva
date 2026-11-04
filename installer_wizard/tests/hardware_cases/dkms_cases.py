import asyncio
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from features.hardware import dkms as dkms_mod
from .common import w


class DkmsTest(unittest.TestCase):
    def test_parse_dkms_conf(self):
        conf = 'PACKAGE_NAME="8812au"\nPACKAGE_VERSION="5.6.4.2"\nAUTOINSTALL="yes"\n'
        self.assertEqual(dkms_mod.parse_dkms_conf(conf), ("8812au", "5.6.4.2"))
        self.assertEqual(dkms_mod.parse_dkms_conf("nulla"), ("", ""))

    def test_url_validation(self):
        v = dkms_mod.validate_git_url
        self.assertTrue(v("https://github.com/aircrack-ng/rtl8812au.git"))
        self.assertFalse(v("http://github.com/x/y.git"))
        self.assertFalse(v("https://evil.example.com/x/y.git"))
        self.assertFalse(v("https://github.com/x/y.git; rm -rf /"))
        self.assertFalse(v("--upload-pack=x"))
        self.assertFalse(v(""))

    def test_headers_packages(self):
        self.assertEqual(dkms_mod.headers_packages("apt", "debian", "6.12.0-amd64")[0], "linux-headers-6.12.0-amd64")
        self.assertEqual(dkms_mod.headers_packages("apt", "ubuntu", "6.8")[1], "linux-headers-generic")
        self.assertEqual(dkms_mod.headers_packages("dnf", "fedora", "6.1")[0], "kernel-devel-6.1")

    def _broker(self, root: Path, fail_step: str = ""):
        calls = []

        async def run(cmd, timeout=180, env=None):
            calls.append(cmd)
            if cmd[:2] == ["git", "init"]:
                src = Path(cmd[-1])
                w(src / "dkms.conf", 'PACKAGE_NAME="rtlfake"\nPACKAGE_VERSION="1.0"\n')
                w(src / "Makefile", "all:\n")
                return 0, "cloned"
            if cmd[0] == "git" and "rev-parse" in cmd:
                return 0, "a" * 40
            if cmd[:2] == ["dkms", "status"]:
                return 0, "rtlfake/1.0, test-kernel, x86_64: installed"
            if cmd[0] == "dkms" and cmd[1] == fail_step:
                return 1, "build error"
            return 0, "ok"

        async def install(pkgs):
            return 0, "ok"

        patcher = mock.patch.object(dkms_mod, "kernel_release", return_value="test-kernel")
        patcher.start()
        self.addCleanup(patcher.stop)
        secure_boot = mock.patch.object(dkms_mod, "secure_boot_permits_sources", new=mock.AsyncMock(return_value=True))
        secure_boot.start()
        self.addCleanup(secure_boot.stop)
        return dkms_mod.DkmsBroker(run, install, src_root=root), calls

    def test_install_from_git_success(self):
        with tempfile.TemporaryDirectory() as d:
            broker, calls = self._broker(Path(d))
            res = asyncio.run(broker.install_from_git({"git": "https://github.com/aircrack-ng/rtl8812au.git", "module": "rtlfake", "revision": "a" * 40}))
            self.assertTrue(res.ok, res.message)
            self.assertEqual((res.dkms_name, res.dkms_version), ("rtlfake", "1.0"))
            self.assertTrue((Path(d) / "rtlfake-1.0" / "Makefile").exists())
            self.assertEqual([c[1] for c in calls if c[0] == "dkms"], ["add", "build", "install", "status"])
            self.assertTrue(any("fetch" in c and "a" * 40 in c for c in calls))

    def test_install_from_git_rolls_back_on_build_failure(self):
        with tempfile.TemporaryDirectory() as d:
            broker, calls = self._broker(Path(d), fail_step="build")
            res = asyncio.run(broker.install_from_git({"git": "https://github.com/aircrack-ng/rtl8812au.git", "module": "rtlfake", "revision": "a" * 40}))
            self.assertFalse(res.ok)
            self.assertIn("dkms build fallito", res.message)
            self.assertFalse((Path(d) / "rtlfake-1.0").exists())
            self.assertIn("remove", [c[1] for c in calls if c[0] == "dkms"])

    def test_rejects_bad_url_without_running_anything(self):
        with tempfile.TemporaryDirectory() as d:
            broker, calls = self._broker(Path(d))
            res = asyncio.run(broker.install_from_git({"git": "http://x.example/a.git"}))
            self.assertFalse(res.ok)
            self.assertEqual(calls, [])
