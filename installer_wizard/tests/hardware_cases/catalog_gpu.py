import unittest
from features.hardware import capabilities as caps_mod
from features.hardware import dkms as dkms_mod
from features.hardware import identify
from features.hardware.accelerators import plan_gpu
from features.hardware.catalog import catalog
from features.hardware.model import HardwareDevice


class CatalogTest(unittest.TestCase):
    def test_find_and_packages(self):
        r = catalog.find("usb", "148F", "2573")
        self.assertEqual(r.id, "ralink-rt73")
        self.assertIn("firmware-misc-nonfree", r.packages_for("apt"))
        self.assertIn("linux-firmware", r.packages_for("yum"))
        self.assertIsNone(catalog.find("usb", "ffff", "ffff"))

    def test_firmware_resolution(self):
        self.assertEqual(catalog.firmware_packages("rtl_nic/rtl8168h-2.fw", "apt"), ["firmware-realtek"])
        self.assertEqual(catalog.firmware_packages("iwlwifi-cc-a0-77.ucode", "apt"), ["firmware-iwlwifi"])
        self.assertEqual(catalog.firmware_packages("rt73.bin", "apt"), ["firmware-misc-nonfree", "firmware-mediatek"])
        self.assertEqual(catalog.firmware_packages("sconosciuto.bin", "apt"), ["firmware-linux-nonfree"])
        self.assertEqual(catalog.firmware_packages("rtl_nic/rtl8168h-2.fw", "dnf"), ["linux-firmware"])

    def test_dkms_recipes_have_safe_git_urls(self):
        dk = [r for r in catalog.recipes if r.dkms]
        self.assertGreaterEqual(len(dk), 3)
        for r in dk:
            self.assertTrue(dkms_mod.validate_git_url(r.dkms["git"]), r.id)


class GpuTest(unittest.TestCase):
    def ident(self, vid, driver):
        return identify.Identity(bus="pci", sys_id="0000:01:00.0", vendor_id=vid, product_id="1c82", category="gpu", bound_driver=driver)

    def test_nvidia_headless_installs_automatically(self):
        p = plan_gpu(self.ident("10de", "nouveau"), "apt", graphical=False)
        self.assertEqual(p.status, "needs_driver")
        self.assertIn("nvidia-driver", p.packages)
        self.assertIn("non-free", p.repos)
        self.assertTrue(p.reboot)

    def test_nvidia_desktop_needs_approval(self):
        p = plan_gpu(self.ident("10de", "nouveau"), "apt", graphical=True)
        self.assertEqual(p.status, "awaiting_approval")
        self.assertTrue(p.needs_approval)

    def test_nvidia_already_ok(self):
        self.assertEqual(plan_gpu(self.ident("10de", "nvidia"), "apt", graphical=True).status, "ready")

    def test_open_drivers(self):
        self.assertEqual(plan_gpu(self.ident("8086", "i915"), "apt").status, "ready")
        self.assertEqual(plan_gpu(self.ident("1002", "amdgpu"), "dnf").status, "ready")
        p = plan_gpu(self.ident("1002", None), "apt", graphical=True)
        self.assertEqual(p.status, "needs_driver")
        self.assertIn("firmware-amd-graphics", p.packages)

    def test_unknown_vendor(self):
        self.assertIsNone(plan_gpu(self.ident("abcd", None), "apt"))


class CapabilityTest(unittest.TestCase):
    def test_only_ready_devices_expose_capabilities(self):
        self.assertEqual(caps_mod.capabilities_for("wifi", "ready"), ["network.wifi"])
        self.assertEqual(caps_mod.capabilities_for("wifi", "needs_driver"), [])
        self.assertEqual(caps_mod.capabilities_for("gpu", "ready", ["compute.accelerator"]), ["graphics.render", "compute.accelerator"])
        self.assertEqual(caps_mod.capabilities_for("other", "ready"), [])

    def test_aggregate(self):
        a = HardwareDevice("a", "A", "", "", "", "wifi", capabilities=["network.wifi"])
        b = HardwareDevice("b", "B", "", "", "", "wifi", capabilities=["network.wifi"])
        self.assertEqual(caps_mod.aggregate([a, b]), {"network.wifi": ["a", "b"]})
