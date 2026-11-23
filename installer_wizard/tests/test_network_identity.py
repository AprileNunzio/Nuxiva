import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agenti.network import explorer as explorer_mod, neighbours, store
from agenti.network.identity import engine, fallback, history


def known(key, mac=None, ip=None, hostname=None):
    return {"key": key, "mac": mac, "ip": ip, "hostname": hostname}


class FallbackVectorsTest(unittest.TestCase):
    def test_mac_normalization_matches_rust(self):
        self.assertEqual(fallback.normalize_mac("AA-BB-CC-DD-EE-FF"), "aa:bb:cc:dd:ee:ff")
        self.assertEqual(fallback.normalize_mac("a0b1.c2d3.e4f5"), "a0:b1:c2:d3:e4:f5")
        for bad in ("ff:ff:ff:ff:ff:ff", "01:00:5e:00:00:01", "zz:bb:cc:dd:ee:ff", "<script>", None, "self"):
            self.assertIsNone(fallback.normalize_mac(bad))
        self.assertTrue(fallback.randomized("da:a1:19:00:00:01"))

    def test_same_mac_new_ip_keeps_identity_and_absorbs_orphan(self):
        items = [known("a0:b1:c2:d3:e4:f5", "a0:b1:c2:d3:e4:f5", "192.168.1.10"), known("ip:192.168.1.50", None, "192.168.1.50")]
        self.assertEqual(fallback.resolve(items, {"mac": "A0:B1:C2:D3:E4:F5", "ip": "192.168.1.50"}),
                         {"key": "a0:b1:c2:d3:e4:f5", "mac": "a0:b1:c2:d3:e4:f5", "randomized": False, "merge": ["ip:192.168.1.50"]})

    def test_rotating_mac_follows_hostname_but_stable_mac_does_not(self):
        items = [known("da:a1:19:00:00:01", "da:a1:19:00:00:01", "192.168.1.20", "iPhone-di-Nunzio.local")]
        self.assertEqual(fallback.resolve(items, {"mac": "de:ad:19:00:00:02", "ip": "192.168.1.31", "hostname": "iphone-di-nunzio"})["key"],
                         "da:a1:19:00:00:01")
        self.assertEqual(fallback.resolve(items, {"mac": "a0:b1:c2:d3:e4:f5", "hostname": "iphone-di-nunzio"})["key"], "a0:b1:c2:d3:e4:f5")

    def test_without_mac(self):
        items = [known("a0:b1:c2:d3:e4:f5", "a0:b1:c2:d3:e4:f5", "192.168.1.10"), known("ip:192.168.1.70", None, "192.168.1.70", "nas")]
        self.assertEqual(fallback.resolve(items, {"ip": "192.168.1.99", "hostname": "NAS.local"})["key"], "ip:192.168.1.70")
        self.assertEqual(fallback.resolve(items, {"ip": "192.168.1.10"})["key"], "a0:b1:c2:d3:e4:f5")
        self.assertEqual(fallback.resolve(items, {"ip": "192.168.1.11"})["key"], "ip:192.168.1.11")
        self.assertIsNone(fallback.resolve(items, {}))
        self.assertEqual(fallback.resolve([known("ip:192.168.1.2", None, "192.168.1.2")], {"ip": "192.168.1.2", "own": True}),
                         {"key": "self", "mac": None, "randomized": False, "merge": ["ip:192.168.1.2"]})

    def test_engine_uses_python_when_native_missing(self):
        with mock.patch.object(engine.native_core, "symbol", return_value=None):
            self.assertEqual(engine.resolve({"ip:10.0.0.5": {"ip": "10.0.0.5"}}, {"mac": "10:20:30:40:50:60", "ip": "10.0.0.5"})["merge"],
                             ["ip:10.0.0.5"])


class NeighboursTest(unittest.TestCase):
    def test_parse_keeps_only_complete_entries(self):
        text = ("IP address       HW type     Flags       HW address            Mask     Device\n"
                "192.168.1.50     0x1         0x2         A0:B1:C2:D3:E4:F5     *        eth0\n"
                "192.168.1.51     0x1         0x0         00:00:00:00:00:00     *        eth0\n"
                "not-an-ip        0x1         0x2         aa:aa:aa:aa:aa:aa     *        eth0\n")
        self.assertEqual(neighbours.parse(text), {"192.168.1.50": "a0:b1:c2:d3:e4:f5"})


class HistoryTest(unittest.TestCase):
    def test_absorb_keeps_user_labels(self):
        device = {"ip": "192.168.1.50", "first_seen": 200, "sessions": [[200, 210]]}
        history.absorb(device, {"name": "TV sala", "room": "Sala", "trusted": True, "first_seen": 100, "sessions": [[100, 110]], "ip": "192.168.1.9"})
        self.assertEqual((device["name"], device["room"], device["trusted"], device["first_seen"]), ("TV sala", "Sala", True, 100))
        self.assertEqual(device["sessions"], [[100, 110], [200, 210]])
        self.assertIn("192.168.1.9", device["ips"])


class ScanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.patches = [mock.patch.object(store, "LEGACY", root / "devices.json"),
                        mock.patch.object(store, "VAULT", store.SealedFile(root / "devices.vault", root / "devices.key"))]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_ip_change_is_not_a_new_device_and_registry_is_sealed(self):
        net = explorer_mod.NetworkExplorer()
        net.devices = {}
        net.subnet, net.own_ip = "192.168.1.0/24", "192.168.1.2"
        rounds = [[{"ip": "192.168.1.40", "mac": "a0:b1:c2:d3:e4:f5", "vendor": "Acme", "own": False}],
                  [{"ip": "192.168.1.77", "mac": "a0:b1:c2:d3:e4:f5", "vendor": "Acme", "own": False}]]
        events = []
        with mock.patch.object(explorer_mod.store, "event", lambda *a: events.append(a)):
            for found in rounds:
                with mock.patch.object(net, "discover", mock.AsyncMock(return_value=found)):
                    asyncio.run(net.scan())
        self.assertEqual(list(net.devices), ["a0:b1:c2:d3:e4:f5"])
        self.assertEqual(net.devices["a0:b1:c2:d3:e4:f5"]["ips"], ["192.168.1.40", "192.168.1.77"])
        self.assertEqual(sum(1 for e in events if "Nuovo dispositivo" in e[1]), 1)
        raw = (Path(self.tmp.name) / "devices.vault").read_bytes()
        self.assertNotIn(b"a0:b1:c2", raw)
        self.assertEqual(store.load()["a0:b1:c2:d3:e4:f5"]["ip"], "192.168.1.77")

    def test_legacy_plain_file_is_migrated(self):
        store.LEGACY.write_text('{"ip:1.2.3.4": {"key": "ip:1.2.3.4", "ip": "1.2.3.4"}}', encoding="utf-8")
        data = store.load()
        store.save(data)
        self.assertFalse(store.LEGACY.exists())
        self.assertIn("ip:1.2.3.4", store.load())


if __name__ == "__main__":
    unittest.main()
