import asyncio
import unittest
from unittest import mock

from features.agency import tuning

ENV = {}


def env(key, default=""):
    return ENV.get(key, default)


class TuningTest(unittest.TestCase):
    def setUp(self):
        ENV.clear()
        patcher = mock.patch.object(tuning, "env_get", env)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_auto_by_default_and_manual_when_chosen(self):
        self.assertEqual(tuning.scheduler(), {"mode": "auto", "manual_parallel": 2, "max_parallel": 16, "reserve_ram_mb": 2048})
        ENV.update({"NUXIVA_AGENCY_PARALLEL": "8", "NUXIVA_AGENCY_MAX_PARALLEL": "32", "NUXIVA_AGENCY_RESERVE_MB": "4096"})
        self.assertEqual(tuning.scheduler(), {"mode": "manual", "manual_parallel": 8, "max_parallel": 32, "reserve_ram_mb": 4096})

    def test_out_of_range_values_fall_back(self):
        ENV.update({"NUXIVA_AGENCY_PARALLEL": "999", "NUXIVA_AGENCY_MAX_PARALLEL": "-1", "NUXIVA_AGENCY_RESERVE_MB": "abc"})
        self.assertEqual(tuning.scheduler(), {"mode": "manual", "manual_parallel": 2, "max_parallel": 16, "reserve_ram_mb": 2048})

    def model_for(self, chain):
        with mock.patch("features.brain.llm.component_chain", mock.AsyncMock(return_value=chain)), \
                mock.patch("features.brain.llm.chain", mock.AsyncMock(return_value=["qwen2.5:7b"])):
            return asyncio.run(tuning.model())

    def test_model_profile_follows_the_brain_choice(self):
        self.assertEqual(self.model_for(["qwen2.5:3b"]), {"kind": "local", "size_mb": int(1.9 * 1024)})
        self.assertEqual(self.model_for([]), {"kind": "local", "size_mb": int(4.7 * 1024)})
        self.assertEqual(self.model_for(["sconosciuto:1b"]), {"kind": "local", "size_mb": tuning.DEFAULT_SIZE_MB})
        with mock.patch("features.cloud.catalog.is_cloud", lambda m: m.startswith("cloud:")):
            ENV["NUXIVA_AGENCY_CLOUD_RPM"] = "120"
            self.assertEqual(self.model_for(["cloud:openai/gpt"]), {"kind": "cloud", "requests_per_minute": 120})

    def test_sync_sends_only_changes(self):
        sent = []

        async def call(op, **fields):
            sent.append((op, fields))
            return {}
        tuner = tuning.Tuner()
        with mock.patch.object(tuning.client, "call", call), mock.patch.object(tuning, "model", mock.AsyncMock(return_value={"kind": "local", "size_mb": 100})):
            self.assertTrue(asyncio.run(tuner.sync()))
            self.assertFalse(asyncio.run(tuner.sync()))
            ENV["NUXIVA_AGENCY_PARALLEL"] = "4"
            self.assertTrue(asyncio.run(tuner.sync()))
        self.assertEqual([op for op, _ in sent], ["settings_set", "settings_set"])
        self.assertEqual(sent[-1][1]["scheduler"]["manual_parallel"], 4)


if __name__ == "__main__":
    unittest.main()
