import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from features.hardware import identify
from .common import ALIAS, PCI_IDS, can_symlink, pci_modalias, usb_modalias, w


class ModaliasTest(unittest.TestCase):
    def test_parse_usb(self):
        f = identify.parse_modalias(usb_modalias("148f", "2573", 0xFF, 0xFF, 0xFF))
        self.assertEqual((f["bus"], f["vendor"], f["product"]), ("usb", "148f", "2573"))
        self.assertEqual(int(f["ic"], 16), 0xFF)

    def test_parse_pci(self):
        f = identify.parse_modalias(pci_modalias("10de", "1c82", 3, 0))
        self.assertEqual((f["bus"], f["vendor"], f["product"], f["bc"]), ("pci", "10de", "1c82", "03"))

    def test_parse_acpi_and_garbage(self):
        self.assertEqual(identify.parse_modalias("acpi:INT3400:")["vendor"], "INT3400")
        self.assertEqual(identify.parse_modalias("rumore"), {})
        self.assertEqual(identify.parse_modalias(""), {})

    def test_class_mapping(self):
        self.assertEqual(identify.pci_class_to_category(0x030000), "gpu")
        self.assertEqual(identify.pci_class_to_category(0x020000), "network")
        self.assertEqual(identify.pci_class_to_category(0x028000), "wifi")
        self.assertEqual(identify.pci_class_to_category(0x040300), "audio")
        self.assertEqual(identify.pci_class_to_category(0x120000), "accelerator")
        self.assertIsNone(identify.pci_class_to_category(0x060000))
        self.assertIsNone(identify.pci_class_to_category(0x0C0330))
        self.assertIsNone(identify.pci_class_to_category(0x078000))
        self.assertIsNone(identify.pci_class_to_category(0x010601))
        self.assertEqual(identify.pci_class_to_category(0x070002), "serial")
        self.assertEqual(identify.usb_class_to_category("1234", 0xE0, 1, 1), "bluetooth")
        self.assertEqual(identify.usb_class_to_category("1234", 0x0E, 1, 0), "camera")
        self.assertEqual(identify.usb_class_to_category("0403", 0xFF, 0xFF, 0xFF), "serial")
        self.assertEqual(identify.usb_class_to_category("1234", 0x07, 1, 2), "printer")


class IdsAndAliasTest(unittest.TestCase):
    def test_ids_database(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "pci.ids"
            w(p, PCI_IDS)
            db = identify.IdsDatabase([str(p)])
            self.assertEqual(db.vendor("8086"), "Intel Corporation")
            self.assertEqual(db.device("8086", "1912"), "HD Graphics 530")
            self.assertEqual(db.device("10EC", "8168"), "RTL8111/8168/8411 PCI Express Gigabit Ethernet")
            self.assertEqual(db.device("8086", "ffff"), "")

    def test_modules_alias_matching(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "modules.alias"
            w(p, ALIAS)
            idx = identify.ModulesAlias(p)
            self.assertEqual(idx.modules_for(usb_modalias("148f", "2573", 0xFF, 0xFF, 0xFF)), ["rt73usb"])
            self.assertEqual(idx.modules_for(pci_modalias("10ec", "8168", 2, 0)), ["r8169"])
            self.assertEqual(idx.modules_for(pci_modalias("8086", "1912", 3, 0)), ["i915"])
            self.assertEqual(idx.modules_for(pci_modalias("8086", "1912", 2, 0)), [])
            self.assertEqual(idx.modules_for("acpi:INT3400:"), ["int3400_thermal"])
            self.assertEqual(idx.modules_for(""), [])
            self.assertTrue(idx.available)


@unittest.skipIf(os.name == "nt", "il sysfs usa ':' nei nomi, non validi su Windows: gira su Linux")
class SysfsScanTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.alias_file = self.root / "modules.alias"
        w(self.alias_file, ALIAS)
        self.alias = identify.ModulesAlias(self.alias_file)

    def tearDown(self):
        self._tmp.cleanup()

    def _usb(self, name, vid, pid, product, ic, isc, ip):
        dev = self.root / "bus" / "usb" / "devices" / name
        w(dev / "idVendor", vid)
        w(dev / "idProduct", pid)
        w(dev / "product", product)
        w(dev / f"{name}:1.0" / "modalias", usb_modalias(vid, pid, ic, isc, ip))
        return dev

    def test_usb_unbound_device_gets_kernel_module(self):
        self._usb("1-6", "148f", "2573", "54M.USB", 0xFF, 0xFF, 0xFF)
        w(self.root / "bus" / "usb" / "devices" / "usb1" / "idVendor", "1d6b")
        w(self.root / "bus" / "usb" / "devices" / "usb1" / "idProduct", "0002")
        found = identify.scan_usb(self.root, self.alias)
        self.assertEqual([i.sys_id for i in found], ["1-6"])
        self.assertEqual(found[0].kernel_modules, ["rt73usb"])
        self.assertIsNone(found[0].bound_driver)

    def test_usb_hub_only_and_camera(self):
        self._usb("1-1", "05e3", "0608", "Hub", 0x09, 0, 0)
        self._usb("1-4", "0c45", "64ab", "Integrated Camera", 0x0E, 1, 0)
        found = identify.scan_usb(self.root, self.alias)
        self.assertEqual([(i.sys_id, i.category) for i in found], [("1-4", "camera")])

    @unittest.skipUnless(can_symlink(), "symlink non permessi")
    def test_usb_bound_driver_detected(self):
        dev = self._usb("1-6", "148f", "2573", "54M.USB", 0xFF, 0xFF, 0xFF)
        drv = self.root / "bus" / "usb" / "drivers" / "rt73usb"
        drv.mkdir(parents=True)
        os.symlink(drv, dev / "1-6:1.0" / "driver")
        found = identify.scan_usb(self.root, self.alias)
        self.assertEqual(found[0].bound_driver, "rt73usb")

    def test_pci_scan_filters_infrastructure(self):
        base = self.root / "bus" / "pci" / "devices"
        for name, cls, vid, did, mod in (
            ("0000:00:02.0", "0x030000", "0x8086", "0x1912", pci_modalias("8086", "1912", 3, 0)),
            ("0000:00:00.0", "0x060000", "0x8086", "0x190f", pci_modalias("8086", "190f", 6, 0)),
            ("0000:01:00.0", "0x020000", "0x10ec", "0x8168", pci_modalias("10ec", "8168", 2, 0)),
        ):
            w(base / name / "class", cls)
            w(base / name / "vendor", vid)
            w(base / name / "device", did)
            w(base / name / "modalias", mod)
        ids = Path(self.root / "pci.ids")
        w(ids, PCI_IDS)
        with mock.patch.object(identify, "pci_ids", identify.IdsDatabase([str(ids)])):
            found = identify.scan_pci(self.root, self.alias)
        self.assertEqual({i.sys_id: i.category for i in found}, {"0000:00:02.0": "gpu", "0000:01:00.0": "network"})
        gpu = next(i for i in found if i.category == "gpu")
        self.assertEqual(gpu.vendor_name, "Intel Corporation")
        self.assertEqual(gpu.kernel_modules, ["i915"])

    def test_acpi_only_reports_unbound_with_module(self):
        base = self.root / "bus" / "acpi" / "devices"
        w(base / "INT3400:00" / "modalias", "acpi:INT3400:")
        w(base / "INT3400:00" / "status", "15")
        w(base / "PNP0C0A:00" / "modalias", "acpi:PNP0C0A:")
        w(base / "INT3400:01" / "modalias", "acpi:INT3400:")
        w(base / "INT3400:01" / "status", "0")
        found = identify.scan_acpi(self.root, self.alias)
        self.assertEqual([i.sys_id for i in found], ["INT3400:00"])
        self.assertEqual(found[0].kernel_modules, ["int3400_thermal"])
