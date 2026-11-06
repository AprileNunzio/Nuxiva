import json
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

for p in (str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[1] / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

import psutil

import machine
import native_core
import sysinfo

NATIVE = native_core.load()
SYMBOLS = ("RustTelemetry", "telemetry_parse_nvidia_smi", "machine_detect", "machine_core_runtime",
           "machine_docker_needed")
READY = NATIVE is not None and all(hasattr(NATIVE, name) for name in SYMBOLS)
GIB = 2 ** 30


@unittest.skipUnless(READY, "modulo nativo telemetry-core non installato")
class TelemetryParityTest(unittest.TestCase):

    def test_snapshot_has_the_same_shape_as_python(self):
        rust = sysinfo.collect()
        with mock.patch.object(native_core, "symbol", return_value=None):
            python = sysinfo._py_collect()
        self.assertEqual(set(rust), set(python))
        self.assertEqual(set(rust["gpu"]), set(python["gpu"]) - {"error"})
        for row in rust["top_processes"]:
            self.assertEqual(set(row), {"pid", "name", "cpu", "mem_mb", "status"})

    def test_static_values_match_psutil(self):
        data = sysinfo.collect()
        self.assertEqual(data["mem_total"], psutil.virtual_memory().total)
        self.assertEqual(data["cpu_count"], psutil.cpu_count())
        self.assertEqual(data["disk_total"], psutil.disk_usage("/").total)
        self.assertEqual(data["swap_total"], psutil.swap_memory().total)
        self.assertLessEqual(abs(data["uptime"] - int(time.time() - psutil.boot_time())), 2)
        self.assertLessEqual(abs(data["mem_percent"] - psutil.virtual_memory().percent), 5)
        self.assertLessEqual(abs(data["disk_percent"] - psutil.disk_usage("/").percent), 1)
        self.assertEqual(len(data["load"]), 3)
        self.assertLessEqual(len(data["top_processes"]), 8)

    def test_second_sample_has_rates_and_percentages_in_range(self):
        sysinfo.collect()
        time.sleep(0.2)
        data = sysinfo.collect()
        self.assertTrue(0 <= data["cpu_percent"] <= 100)
        self.assertTrue(all(0 <= v <= 100 for v in data["per_cpu"]))
        self.assertGreaterEqual(data["net_rx_rate"], 0)

    def test_nvidia_parsing_matches(self):
        native = NATIVE.telemetry_parse_nvidia_smi
        parsed = json.loads(native("NVIDIA GeForce RTX 4090, 37, 2048, 24564, 61, 2520"))
        self.assertEqual(parsed, {"name": "NVIDIA GeForce RTX 4090", "gpu_percent": 37.0, "vram_used": 2048.0,
                                  "vram_total": 24564.0, "vram_percent": round(2048 / 24564 * 100, 1),
                                  "temp": 61.0, "clock_mhz": 2520.0, "available": True})
        self.assertIsNone(native("[N/A], 1"))
        self.assertIsNone(native("x, [N/A], 1, 2, 3, 4"))

    def test_machine_rules_match(self):
        for board in ("", "Raspberry Pi 5 Model B"):
            for ram in (2, 7, 8, 16, 27, 28, 64):
                for gpu in (False, True):
                    with self.subTest(board=board, ram=ram, gpu=gpu), \
                            mock.patch.object(machine, "board", return_value=board), \
                            mock.patch.object(machine.psutil, "virtual_memory",
                                              return_value=mock.Mock(total=ram * GIB)):
                        rust = machine.detect(gpu)
                        with mock.patch.object(native_core, "symbol", return_value=None):
                            python = machine.detect(gpu)
                        self.assertEqual(rust, python)
        for env in ({}, {"NUXIVA_MACHINE": "pi"}, {"NUXIVA_MACHINE": "powerful"}, {"NUXIVA_CORE_RUNTIME": "docker"},
                    {"NUXIVA_MACHINE": "small", "NUXIVA_CORE_RUNTIME": "bogus"}, {"NUXIVA_SANDBOX": " Auto "},
                    {"NUXIVA_MACHINE": "small", "NUXIVA_SANDBOX": "0"}, {"NUXIVA_MACHINE": "pi", "NUXIVA_SANDBOX": "yes"}):
            with self.subTest(env=env):
                rust = (machine.core_runtime(env), machine.docker_needed(env))
                with mock.patch.object(native_core, "symbol", return_value=None):
                    python = (machine.core_runtime(env), machine.docker_needed(env))
                self.assertEqual(rust, python)


class TelemetryFallbackTest(unittest.TestCase):

    def test_python_engine_still_collects(self):
        with mock.patch.object(native_core, "symbol", return_value=None):
            data = sysinfo.collect()
        self.assertIn("mem_total", data)
        self.assertGreater(data["mem_total"], 0)


if __name__ == "__main__":
    unittest.main()
