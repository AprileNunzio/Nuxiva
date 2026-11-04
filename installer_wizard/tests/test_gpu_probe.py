import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from server.features.mesh_coordinator import gpu_probe


def _card(root: Path, name: str, vendor: str, slot: str, **files: str) -> None:
    device = root / name / "device"
    device.mkdir(parents=True)
    (device / "vendor").write_text(vendor)
    (device / "uevent").write_text(f"DRIVER=x\nPCI_SLOT_NAME={slot}\n")
    for key, value in files.items():
        (device / key).write_text(value)


class GpuProbeTest(unittest.TestCase):
    def test_parse_nvidia_rows(self):
        out = "NVIDIA GeForce RTX 4090, 11776, 24564, 412.50, 37, 64\nTesla T4, 0, 15360, [N/A], 0, 41\n"
        gpus = gpu_probe.parse_nvidia(out)
        self.assertEqual([g.name for g in gpus], ["NVIDIA GeForce RTX 4090", "Tesla T4"])
        self.assertEqual(gpus[0].vram_total_gb, 23.99)
        self.assertEqual(gpus[0].power_watts, 412.5)
        self.assertIsNone(gpus[1].power_watts)

    def test_parse_nvidia_ignores_garbage(self):
        self.assertEqual(gpu_probe.parse_nvidia("No devices were found\n"), [])

    def test_drm_detects_amd_and_intel(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _card(root, "card0", "0x1002", "0000:03:00.0", mem_info_vram_total=str(16 * 2**30),
                  mem_info_vram_used=str(2 * 2**30), gpu_busy_percent="12")
            _card(root, "card1", "0x8086", "0000:00:02.0")
            _card(root, "card2", "0x10de", "0000:01:00.0")
            (root / "card0-DP-1").mkdir()
            gpus = gpu_probe.drm_gpus(root, namer=lambda slot: "", skip_nvidia=True)
        self.assertEqual([(g.vendor, g.name) for g in gpus], [("AMD", "AMD GPU"), ("Intel", "Intel GPU")])
        self.assertEqual(gpus[0].vram_total_gb, 16.0)
        self.assertEqual(gpus[0].utilization, 12.0)

    def test_summary_counts_every_gpu(self):
        fake = [gpu_probe.GpuInfo("A", "NVIDIA", 1.0, 8.0, 100.0), gpu_probe.GpuInfo("B", "AMD", 2.0, 16.0)]
        probe = gpu_probe.GpuProbe()
        with mock.patch.object(gpu_probe, "_nvidia", return_value=fake[:1]), \
                mock.patch.object(gpu_probe, "drm_gpus", return_value=fake[1:]):
            summary = probe.summary()
        self.assertEqual(summary["gpu_count"], 2)
        self.assertEqual(summary["gpu_name"], "A")
        self.assertEqual(summary["vram_total_gb"], 24.0)
        self.assertEqual(summary["gpu_power_watts"], 100.0)

    def test_no_gpu_reports_zero(self):
        probe = gpu_probe.GpuProbe()
        with mock.patch.object(gpu_probe, "_nvidia", return_value=[]), mock.patch.object(gpu_probe, "drm_gpus", return_value=[]):
            summary = probe.summary()
        self.assertEqual(summary["gpu_count"], 0)
        self.assertIsNone(summary["gpu_name"])


if __name__ == "__main__":
    unittest.main()
