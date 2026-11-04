import unittest

from features.activation.application.capability_security_manager import CapabilitySecurityManager
from features.activation.application.cognitive_memory_manager import CognitiveMemoryScheduler
from features.activation.domain.capability_tokens import CapabilityScope
from features.activation.domain.memory_scheduler import ModelAllocation, ModelKind, ModelPriority


class AdvancedOSCapabilitiesTests(unittest.TestCase):
    def test_cognitive_memory_scheduler_vram_paging(self):
        scheduler = CognitiveMemoryScheduler(total_vram_mb=8192, total_ram_mb=16384)

        whisper = ModelAllocation(ModelKind.WHISPER, vram_mb=2048, ram_mb=1024, priority=ModelPriority.STANDBY)
        deep_brain = ModelAllocation(ModelKind.DEEP_BRAIN, vram_mb=6144, ram_mb=2048, priority=ModelPriority.ACTIVE_INTERACTION)
        vision = ModelAllocation(ModelKind.VISION, vram_mb=3072, ram_mb=1024, priority=ModelPriority.EMERGENCY_REALTIME)

        scheduler.register_model(whisper)
        scheduler.register_model(deep_brain)
        scheduler.register_model(vision)

        scheduler.schedule_interaction(ModelKind.WHISPER)
        self.assertEqual(scheduler.current_vram_usage, 2048)

        scheduler.schedule_interaction(ModelKind.DEEP_BRAIN)
        self.assertEqual(scheduler.current_vram_usage, 8192)

        evicted = scheduler.schedule_interaction(ModelKind.VISION)
        self.assertIn(ModelKind.WHISPER, evicted)
        self.assertTrue(scheduler.current_vram_usage <= 8192)

    def test_capability_security_manager_token_verification(self):
        secret = b"k" * 32
        manager = CapabilitySecurityManager(secret)

        token = manager.issue_grant(
            scope=CapabilityScope.NETWORK_HTTP,
            target_pattern="https://api.weather.com/",
            ttl_seconds=30.0,
            max_bytes=50_000,
        )

        self.assertTrue(manager.verify_request(token, CapabilityScope.NETWORK_HTTP, "https://api.weather.com/v1/forecast", 1024))
        self.assertFalse(manager.verify_request(token, CapabilityScope.NETWORK_HTTP, "https://malicious-site.com/", 1024))
        self.assertFalse(manager.verify_request(token, CapabilityScope.NETWORK_HTTP, "https://api.weather.com/v1/data", 100_000))
        self.assertFalse(manager.verify_request(token, CapabilityScope.FILESYSTEM_READ, "/etc/passwd", 100))


if __name__ == "__main__":
    unittest.main()
