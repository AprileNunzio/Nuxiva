import asyncio
import tempfile
import unittest
from pathlib import Path
from features.hardware.repos import OsInfo, RepoManager, enable_components_in_deb822, enable_components_in_sources, map_components
from .common import DEB822, DEBIAN11, DEBIAN13, SOURCES, UBUNTU, w


class RepoTest(unittest.TestCase):
    def test_debian_adds_components_only_to_official_mirrors(self):
        text, added = enable_components_in_sources(SOURCES, ["contrib", "non-free"], DEBIAN13)
        self.assertEqual(sorted(added), ["contrib", "non-free"])
        self.assertIn("deb http://deb.debian.org/debian/ trixie main non-free-firmware contrib non-free", text)
        self.assertIn("deb http://security.debian.org/debian-security trixie-security main non-free-firmware contrib non-free", text)
        self.assertIn("deb [arch=amd64] https://download.docker.com/linux/debian trixie stable\n", text)
        self.assertIn("#deb cdrom:", text)

    def test_idempotent(self):
        once, _ = enable_components_in_sources(SOURCES, ["contrib", "non-free"], DEBIAN13)
        twice, added = enable_components_in_sources(once, ["contrib", "non-free"], DEBIAN13)
        self.assertEqual(once, twice)
        self.assertEqual(added, [])

    def test_deb822(self):
        text, added = enable_components_in_deb822(DEB822, ["non-free-firmware"], DEBIAN13)
        self.assertEqual(added, ["non-free-firmware"])
        self.assertIn("Components: main non-free-firmware", text)
        self.assertIn("Components: stable\n", text + "\n")

    def test_component_mapping(self):
        self.assertEqual(map_components(["non-free", "contrib"], UBUNTU), (["multiverse", "universe"], []))
        self.assertEqual(map_components(["non-free-firmware"], DEBIAN11), ([], ["non-free-firmware"]))
        self.assertEqual(map_components(["non-free-firmware", "bogus"], DEBIAN13), (["non-free-firmware"], []))

    def test_manager_backup_and_restore(self):
        async def run(cmd, **kw):
            return 0, ""

        with tempfile.TemporaryDirectory() as d:
            apt = Path(d)
            w(apt / "sources.list", SOURCES)
            mgr = RepoManager(run, DEBIAN13, apt_dir=str(apt))
            self.assertFalse(mgr.apt_status()["non-free"])
            res = asyncio.run(mgr.ensure(["non-free", "contrib"], "apt"))
            self.assertTrue(res.changed)
            self.assertEqual(len(res.backups), 1)
            self.assertTrue(mgr.apt_status()["non-free"])
            self.assertIn("non-free", (apt / "sources.list").read_text())
            restored = mgr.restore(res.backups)
            self.assertEqual(len(restored), 1)
            self.assertEqual((apt / "sources.list").read_text(), SOURCES)

            self.assertTrue(asyncio.run(mgr.ensure(["non-free"], "apt")).changed)

            self.assertFalse(asyncio.run(mgr.ensure(["non-free"], "apt")).changed)

    def test_unsupported_manager_is_reported(self):
        async def run(cmd, **kw):
            return 0, ""

        res = asyncio.run(RepoManager(run, OsInfo("arch"), apt_dir="/nonexistent").ensure(["non-free"], "pacman"))
        self.assertFalse(res.changed)
        self.assertEqual(res.unsupported, ["non-free"])

    def test_fedora_installs_rpmfusion(self):
        calls = []

        async def run(cmd, **kw):
            calls.append(cmd)
            return (1, "") if cmd[:2] == ["rpm", "-q"] else (0, "ok")

        mgr = RepoManager(run, OsInfo("fedora", [], "41"), apt_dir="/nonexistent")
        res = asyncio.run(mgr.ensure(["non-free"], "dnf"))
        self.assertTrue(res.changed)
        self.assertEqual(res.enabled, ["rpmfusion-free-release", "rpmfusion-nonfree-release"])
        self.assertTrue(any("rpmfusion-nonfree-release-41.noarch.rpm" in " ".join(c) for c in calls))
