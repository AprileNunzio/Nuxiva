import json
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from features.brain.free_router import capability_matrix, failover_engine
from features.brain.free_router.catalog_poller import normalize_model
from features.brain.free_router.rate_limiter import RateLimiter

INSTALLER_DIR = Path(__file__).resolve().parents[1]


class FreeRouterCatalogTests(unittest.TestCase):
    def test_zero_cost_catalog_filter(self):
        free = normalize_model({"id": "vendor/free-model", "pricing": {"prompt": "0", "completion": "0"},
                                "context_length": 32768, "supported_parameters": ["tools", "response_format"]})
        paid = normalize_model({"id": "vendor/paid-model", "pricing": {"prompt": "0.000001", "completion": "0"}})
        invalid = normalize_model({"id": "bad model", "pricing": {"prompt": "0", "completion": "0"}})
        self.assertIsNotNone(free)
        self.assertIsNone(paid)
        self.assertIsNone(invalid)

    def test_vision_and_tool_capabilities_survive_candidate_selection(self):
        models = [
            {"id": "text-only", "context": 64000, "tools": True, "json": True, "vision": False, "reasoning": True},
            {"id": "vision-tools", "context": 64000, "tools": True, "json": True, "vision": True, "reasoning": True},
        ]
        self.assertEqual([row["id"] for row in capability_matrix.candidates(models, "vision")], ["vision-tools"])
        self.assertEqual([row["id"] for row in capability_matrix.candidates(models, "agent_tools")], ["text-only", "vision-tools"])

    def test_isolated_i18n_keys_match_in_all_languages(self):
        directories = [
            INSTALLER_DIR / "features/brain/free_router/language",
            INSTALLER_DIR / "web/display/widgets/live_brain_badge/language",
            INSTALLER_DIR / "web/display/widgets/token_usage/language",
            *sorted((INSTALLER_DIR.parent / "client_web/src/features/brain_center").rglob("language")),
        ]
        expected_locales = {"it.json", "en.json", "fr.json", "es.json"}
        for directory in directories:
            files = {path.name for path in directory.glob("*.json")}
            self.assertEqual(files, expected_locales)
            dictionaries = [json.loads(path.read_text(encoding="utf-8"))["dictionary"] for path in directory.glob("*.json")]
            self.assertTrue(all(set(dictionary) == set(dictionaries[0]) for dictionary in dictionaries[1:]))

    def test_preemptive_cooldown_skips_network_candidate_without_waiting(self):
        limiter = RateLimiter()
        limiter.observe("openrouter", "exhausted", {
            "x-ratelimit-remaining-requests": "0",
            "x-ratelimit-reset-requests": "30s",
        }, now=100)
        start = time.perf_counter()
        first = limiter.available("openrouter", "exhausted", now=101)
        elapsed_ms = (time.perf_counter() - start) * 1000
        second = limiter.available("openrouter", "available", now=101)
        self.assertFalse(first)
        self.assertTrue(second)
        self.assertLess(elapsed_ms, 5)


class FreeRouterFailoverTests(unittest.IsolatedAsyncioTestCase):
    async def test_connection_reset_retries_compatible_candidate_before_output(self):
        models = [
            {"id": "text-only-vision", "context": 64000, "tools": True, "json": True, "vision": False},
            {"id": "vision-primary", "context": 64000, "tools": True, "json": True, "vision": True},
            {"id": "vision-backup", "context": 64000, "tools": True, "json": True, "vision": True},
        ]
        called = []

        async def call(model):
            called.append(model["id"])
            if model["id"] == "vision-primary":
                raise ConnectionResetError("upstream closed before response commit")
            return "completed response"

        metrics = {"vision-primary": {"quota_pct": 100}, "vision-backup": {"quota_pct": 50}}
        limiter = RateLimiter()
        with patch.object(failover_engine.telemetry_emitter, "emit", return_value={}), \
                patch.object(failover_engine.rate_limiter, "rate_limiter", limiter), \
                patch.object(limiter, "metrics", return_value=metrics):
            result = await failover_engine.run(models, "vision", call)
        self.assertEqual(result, "completed response")
        self.assertEqual(called, ["vision-primary", "vision-backup"])


if __name__ == "__main__":
    unittest.main()
