import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock
import psutil

from node_network_probe import (
    inspect_system_network_interfaces,
    parse_ip_route_output,
    parse_nmcli_devices,
    parse_proc_net_route,
    parse_resolv_conf,
    parse_resolvectl_dns,
)

_VISION_DIR = Path(__file__).resolve().parents[1] / "features" / "vision"


def _load_vision_mod(name: str):
    spec = importlib.util.spec_from_file_location(f"vision_{name}", _VISION_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


selection = _load_vision_mod("selection")
tracks = _load_vision_mod("tracks")
Track = tracks.Track


class VisionProximityHysteresisTest(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.pop("NUXIVA_VISION_NEAR_RATIO", None)
        os.environ.pop("NUXIVA_VISION_NEAR_EXIT_RATIO", None)
        os.environ.pop("NUXIVA_VISION_NEAR_HOLD_S", None)

    def test_calibrated_defaults_and_env_overrides(self) -> None:
        self.assertAlmostEqual(selection.near_enter_ratio(), 0.08)
        self.assertAlmostEqual(selection.near_exit_ratio(), 0.0624)
        self.assertAlmostEqual(selection.near_hold_seconds(), 6.0)
        with mock.patch.dict(os.environ, {"NUXIVA_VISION_NEAR_RATIO": "0.10", "NUXIVA_VISION_NEAR_HOLD_S": "9"}):
            self.assertAlmostEqual(selection.near_enter_ratio(), 0.10)
            self.assertAlmostEqual(selection.near_exit_ratio(), 0.078)
            self.assertAlmostEqual(selection.near_hold_seconds(), 9.0)

    def test_normal_distance_triggers_near_and_hysteresis_prevents_flicker(self) -> None:
        track = Track((100, 100, 66, 66))
        t0 = 1000.0
        prox1, near1 = track.update_proximity(0.104, t0, enter_ratio=0.08, exit_ratio=0.0624, hold_s=6.0)
        self.assertTrue(near1)
        self.assertGreaterEqual(prox1, 0.08)

        _, near2 = track.update_proximity(0.068, t0 + 1.0, enter_ratio=0.08, exit_ratio=0.0624, hold_s=6.0)
        self.assertTrue(near2)

        _, near3 = track.update_proximity(0.045, t0 + 2.0, enter_ratio=0.08, exit_ratio=0.0624, hold_s=6.0)
        self.assertTrue(near3)

        for step in range(1, 8):
            _, near_late = track.update_proximity(0.035, t0 + 6.0 + step, enter_ratio=0.08, exit_ratio=0.0624, hold_s=6.0)
        self.assertFalse(near_late)


class PosixNetworkProbeTest(unittest.TestCase):
    def test_parse_proc_net_route_little_endian_hex(self) -> None:
        sample = (
            "Iface\tDestination\tGateway \tFlags\tRefCnt\tUse\tMetric\tMask\t\tMTU\tWindow\tIRTT\n"
            "eth0\t00000000\tFE01A8C0\t0003\t0\t0\t100\t00000000\t0\t0\t0\n"
            "eth0\t0001A8C0\t00000000\t0001\t0\t0\t100\t00FFFFFF\t0\t0\t0\n"
        )
        gws, default_gw = parse_proc_net_route(sample)
        self.assertEqual(default_gw, "192.168.1.254")
        self.assertEqual(gws.get("eth0"), "192.168.1.254")

    def test_parse_ip_route_json_and_text(self) -> None:
        j_out = '[{"dst":"default","gateway":"192.168.1.254","dev":"enp3s0","metric":100}]'
        gws, def_gw = parse_ip_route_output(j_out, "")
        self.assertEqual(def_gw, "192.168.1.254")
        self.assertEqual(gws["enp3s0"], "192.168.1.254")

        t_out = "default via 192.168.1.254 dev wlan0 proto dhcp src 192.168.1.42 metric 600\n"
        gws2, def_gw2 = parse_ip_route_output("", t_out)
        self.assertEqual(def_gw2, "192.168.1.254")
        self.assertEqual(gws2["wlan0"], "192.168.1.254")

    def test_parse_resolv_conf_skips_systemd_stub_when_upstream_present(self) -> None:
        resolv_text = "nameserver 127.0.0.53\nnameserver 192.168.1.254\nnameserver 9.9.9.9\n"
        dns = parse_resolv_conf(resolv_text)
        self.assertEqual(dns, ["192.168.1.254", "9.9.9.9"])

    def test_parse_resolvectl_and_nmcli(self) -> None:
        r_out = "Global:\nLink 2 (enp3s0): 192.168.1.254\n"
        per_if, glob_dns = parse_resolvectl_dns(r_out)
        self.assertEqual(per_if["enp3s0"], ["192.168.1.254"])
        self.assertEqual(glob_dns, ["192.168.1.254"])

        nm_out = (
            "GENERAL.DEVICE:enp3s0\n"
            "GENERAL.TYPE:ethernet\n"
            "IP4.GATEWAY:192.168.1.254\n"
            "IP4.DNS[1]:192.168.1.254\n"
        )
        gws, dns_map, kinds = parse_nmcli_devices(nm_out)
        self.assertEqual(gws["enp3s0"], "192.168.1.254")
        self.assertEqual(dns_map["enp3s0"], ["192.168.1.254"])
        self.assertEqual(kinds["enp3s0"], "ethernet")

    def test_linux_inspect_never_uses_fake_gateway_or_dns(self) -> None:
        fake_addrs = {
            "enp3s0": [
                SimpleNamespace(family=2, address="192.168.1.50", netmask="255.255.255.0"),
                SimpleNamespace(family=-1, address="aa:bb:cc:dd:ee:ff", netmask=None),
            ]
        }
        fake_stats = {"enp3s0": SimpleNamespace(isup=True, speed=1000, mtu=1500)}
        fake_cnt = {"enp3s0": SimpleNamespace(bytes_recv=1024, bytes_sent=2048)}

        def fake_run(cmd, **kwargs):
            joined = " ".join(cmd)
            if "route show default" in joined:
                return SimpleNamespace(returncode=0, stdout='[{"dst":"default","gateway":"192.168.1.254","dev":"enp3s0","metric":100}]')
            if "nmcli" in joined:
                return SimpleNamespace(
                    returncode=0,
                    stdout="GENERAL.DEVICE:enp3s0\nGENERAL.TYPE:ethernet\nIP4.GATEWAY:192.168.1.254\nIP4.DNS[1]:192.168.1.254\n",
                )
            if "addr show" in joined:
                return SimpleNamespace(returncode=0, stdout='[{"ifname":"enp3s0","addr_info":[{"family":"inet","dynamic":true}]}]')
            return SimpleNamespace(returncode=1, stdout="")

        with mock.patch("os.name", "posix"), \
             mock.patch("psutil.net_if_addrs", return_value=fake_addrs), \
             mock.patch("psutil.net_if_stats", return_value=fake_stats), \
             mock.patch("psutil.net_io_counters", return_value=fake_cnt):
            ifaces = inspect_system_network_interfaces("192.168.1.50", run_cmd=fake_run)

        self.assertEqual(len(ifaces), 1)
        eth = ifaces[0]
        self.assertEqual(eth["gateway"], "192.168.1.254")
        self.assertEqual(eth["dns_primary"], "192.168.1.254")
        self.assertIsNone(eth["dns_secondary"])
        self.assertNotEqual(eth["gateway"], "192.168.1.1")
        self.assertNotEqual(eth["dns_primary"], "1.1.1.1")


if __name__ == "__main__":
    unittest.main()
