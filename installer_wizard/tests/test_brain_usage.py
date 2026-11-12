import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sealed import SealedFile

from features.brain.usage.ledger import BudgetError, UsageLedger, provider_of
from features.cloud.catalog import BY_ID

HEADERS = {"X-Nuxiva-Request": "1"}


class Clock:
    def __init__(self, now: float) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


class BrainUsageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.TemporaryDirectory()
        root = Path(self.dir.name)
        self.sealed = SealedFile(root / "usage.vault", root / "usage.key")
        self.clock = Clock(1_793_000_000.0)
        self.ledger = UsageLedger(self.sealed, self.clock)

    def tearDown(self) -> None:
        self.dir.cleanup()

    def test_provider_of_distinguishes_local_and_cloud(self):
        self.assertEqual(provider_of("qwen2.5:7b"), "local")
        self.assertEqual(provider_of("cloud:openai/gpt-5"), "openai")

    def test_records_are_encrypted_on_disk_and_reloaded(self):
        self.ledger.record("cloud:openai/gpt-5", 100, 50)
        raw = (Path(self.dir.name) / "usage.vault").read_bytes()
        self.assertNotIn(b"openai", raw)
        reloaded = UsageLedger(self.sealed, self.clock)
        summary = reloaded.summary()
        self.assertEqual(summary["cloud"], 150)
        self.assertEqual(summary["providers"][0]["calls"], 1)

    def test_provider_budget_blocks_only_that_provider(self):
        self.ledger.set_budgets({"providers": {"openai": 100}})
        self.ledger.record("cloud:openai/gpt-5", 80, 30)
        self.assertFalse(self.ledger.allows("cloud:openai/gpt-5"))
        self.assertTrue(self.ledger.allows("cloud:anthropic/claude-haiku-5-5"))
        self.assertTrue(self.ledger.allows("qwen2.5:7b"))

    def test_global_budget_ignores_local_models(self):
        self.ledger.set_budgets({"global": 1000})
        self.ledger.record("qwen2.5:7b", 5000, 5000)
        self.assertTrue(self.ledger.allows("cloud:openai/gpt-5"))
        self.ledger.record("cloud:openai/gpt-5", 600, 400)
        self.assertFalse(self.ledger.allows("cloud:mistral/mistral-small-latest"))

    def test_new_month_resets_spending(self):
        self.ledger.set_budgets({"providers": {"openai": 10}})
        self.ledger.record("cloud:openai/gpt-5", 10, 10)
        self.clock.now += 40 * 86400
        self.assertTrue(self.ledger.allows("cloud:openai/gpt-5"))

    def test_invalid_budgets_are_rejected(self):
        for body in ({"global": -1}, {"global": "10"}, {"global": True}, {"providers": {"nope": 10}}, {"providers": []}):
            with self.assertRaises(BudgetError):
                self.ledger.set_budgets(body)

    def test_garbage_token_counts_are_ignored(self):
        self.ledger.record("cloud:openai/gpt-5", "x", None)
        self.assertEqual(self.ledger.summary()["cloud"], 0)
        self.assertEqual(self.ledger.summary()["providers"][0]["calls"], 1)

    def test_old_days_are_pruned(self):
        self.ledger.record("cloud:openai/gpt-5", 1, 1)
        self.clock.now += 100 * 86400
        self.ledger.record("cloud:openai/gpt-5", 1, 1)
        self.assertEqual(len(UsageLedger(self.sealed, self.clock).summary()["days"]), 1)

    def test_compact_reports_budget_share(self):
        self.ledger.set_budgets({"global": 200})
        self.ledger.record("cloud:openai/gpt-5", 50, 50)
        compact = self.ledger.compact()
        self.assertEqual(compact["used"], 0.5)
        self.assertEqual(compact["top"], "openai")

    def test_new_providers_are_in_catalog(self):
        for pid in ("ai21", "upstage", "minimax", "nebius", "github", "cloudflare", "bedrock", "volcengine"):
            self.assertIn(pid, BY_ID)


if __name__ == "__main__":
    unittest.main()


class BrainUsageApiTests(unittest.TestCase):
    def setUp(self) -> None:
        from fastapi.testclient import TestClient

        import nuxiva_supervisor
        from features.brain.usage import ledger as ledger_module

        self.dir = tempfile.TemporaryDirectory()
        root = Path(self.dir.name)
        self.ledger = UsageLedger(SealedFile(root / "u.vault", root / "u.key"))
        self.patch = mock.patch.object(ledger_module, "usage_ledger", self.ledger)
        self.patch.start()
        import features.brain.usage.api as usage_api
        self.api_patch = mock.patch.object(usage_api, "usage_ledger", self.ledger)
        self.api_patch.start()
        self.client = TestClient(nuxiva_supervisor.admin)
        self.client.post("/api/auth/login", json={"username": "admin", "password": "nuxiva"}, headers=HEADERS)

    def tearDown(self) -> None:
        self.api_patch.stop()
        self.patch.stop()
        self.dir.cleanup()

    def test_budget_endpoint_requires_auth_and_validates(self):
        from fastapi.testclient import TestClient

        import nuxiva_supervisor
        anonymous = TestClient(nuxiva_supervisor.admin)
        self.assertEqual(anonymous.put("/api/brains/usage/budgets", json={"global": 10}, headers=HEADERS).status_code, 401)
        self.assertEqual(self.client.put("/api/brains/usage/budgets", json={"global": -4}, headers=HEADERS).status_code, 400)
        ok = self.client.put("/api/brains/usage/budgets", json={"global": 5000, "providers": {"openai": 100}}, headers=HEADERS)
        self.assertEqual(ok.status_code, 200, ok.text)
        self.assertEqual(ok.json()["budgets"], {"global": 5000, "providers": {"openai": 100}})

    def test_summary_reports_recorded_tokens(self):
        self.ledger.record("cloud:openai/gpt-5", 7, 3)
        body = self.client.get("/api/brains/usage").json()
        self.assertEqual(body["cloud"], 10)

    def test_brain_config_exposes_live_revision(self):
        body = self.client.get("/api/v2/brain/config").json()
        self.assertRegex(body["revision"], r"^[0-9a-f]{16}$")
        self.assertIn("working", body)
