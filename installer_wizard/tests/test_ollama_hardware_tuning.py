import unittest
from pathlib import Path

from features.ollama.hardware import calculate_hardware_profile, detect_cpu, detect_memory
from features.ollama.service import (
    generate_systemd_override,
    get_default_config,
    get_runtime_options,
)
from features.ollama.types import OllamaRuntimeConfig


class TestOllamaHardwareTuning(unittest.TestCase):
    def test_cpu_and_memory_detection(self):
        cpu = detect_cpu()
        self.assertGreaterEqual(cpu.physical_cores, 1)
        self.assertGreaterEqual(cpu.logical_cores, 1)
        self.assertIsInstance(cpu.has_avx2, bool)

        mem = detect_memory()
        self.assertGreater(mem.total_bytes, 0)
        self.assertGreater(mem.total_gb, 0.0)

    def test_calculate_hardware_profile(self):
        profile = calculate_hardware_profile()
        self.assertIn(profile.tier, ("lightweight", "balanced", "enterprise"))
        self.assertGreaterEqual(profile.recommended_parallel, 2)
        self.assertGreaterEqual(profile.recommended_context, 4096)
        self.assertGreaterEqual(profile.recommended_max_tokens, 2048)
        self.assertIsInstance(profile.recommended_flash_attention, bool)
        self.assertGreaterEqual(profile.recommended_threads, 1)

    def test_runtime_config_serialization(self):
        cfg = get_default_config()
        d = cfg.to_dict()
        restored = OllamaRuntimeConfig.from_dict(d)
        self.assertEqual(cfg.num_parallel, restored.num_parallel)
        self.assertEqual(cfg.num_ctx, restored.num_ctx)
        self.assertEqual(cfg.flash_attention, restored.flash_attention)

    def test_systemd_override_generation(self):
        cfg = OllamaRuntimeConfig(
            num_parallel=4,
            num_ctx=16384,
            num_predict=4096,
            max_loaded_models=3,
            flash_attention=True,
            keep_alive="24h",
            cpu_weight=100,
            nice=0,
            num_thread=8,
            max_queue=512,
        )
        override = generate_systemd_override(cfg)
        self.assertIn('Environment="OLLAMA_NUM_PARALLEL=4"', override)
        self.assertIn('Environment="OLLAMA_KEEP_ALIVE=24h"', override)
        self.assertIn('Environment="OLLAMA_MAX_LOADED_MODELS=3"', override)
        self.assertIn('Environment="OLLAMA_FLASH_ATTENTION=1"', override)
        self.assertIn('Environment="OLLAMA_MAX_QUEUE=512"', override)
        self.assertIn("CPUWeight=100", override)
        self.assertIn("Nice=0", override)
        self.assertNotIn("Nice=5", override)
        self.assertNotIn("CPUWeight=40", override)

    def test_runtime_options_deep_and_fast(self):
        opts_deep = get_runtime_options(kind="deep")
        self.assertIn("num_ctx", opts_deep)
        self.assertIn("num_predict", opts_deep)
        self.assertIn("num_thread", opts_deep)
        self.assertGreaterEqual(opts_deep["num_ctx"], 4096)

        opts_fast = get_runtime_options(kind="fast")
        self.assertLessEqual(opts_fast["num_predict"], 1024)

    def test_script_50_ollama_unthrottled(self):
        script_path = Path(__file__).resolve().parents[2] / "scripts" / "os" / "steps" / "50-ollama.sh"
        self.assertTrue(script_path.is_file())
        text = script_path.read_text(encoding="utf-8")
        self.assertIn("OLLAMA_NUM_PARALLEL", text)
        self.assertIn("OLLAMA_MAX_QUEUE=512", text)
        self.assertIn("Nice=0", text)
        self.assertIn("CPUWeight=100", text)
        self.assertNotIn("Nice=5", text)
        self.assertNotIn("CPUWeight=40", text)
        self.assertNotIn('OLLAMA_NUM_PARALLEL="1"', text)
