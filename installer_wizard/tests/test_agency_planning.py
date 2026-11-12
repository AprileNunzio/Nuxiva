import unittest
from unittest.mock import AsyncMock, patch

from agenti.agency import blueprint, service, tools, worker


class AgencyPlanningTests(unittest.IsolatedAsyncioTestCase):
    def test_blueprint_parses_decisions_and_questions(self):
        raw = {
            "title": "Shop",
            "summary": "E-commerce platform",
            "architecture": "Rust and Svelte",
            "roles": [{"id": "backend", "mission": "API dev"}],
            "decisions": [
                {
                    "id": "db",
                    "title": "Database Engine",
                    "rationale": "PostgreSQL for ACID compliance",
                    "status": "accepted",
                }
            ],
            "questions": [
                {
                    "id": "payment",
                    "prompt": "Which payment provider should be integrated?",
                    "options": [
                        {"id": "stripe", "label": "Stripe", "description": "Global"},
                        {"id": "paypal", "label": "PayPal", "description": "Alternative"},
                    ],
                }
            ],
            "tasks": [
                {
                    "id": "api",
                    "title": "REST API",
                    "role": "backend",
                    "estimate_seconds": 300,
                    "budget_tokens": 5000,
                    "budget_seconds": 120,
                    "acceptance": ["API tests pass"],
                }
            ],
        }
        bp = blueprint.parse(raw, "Shop")
        self.assertEqual(len(bp.decisions), 1)
        self.assertEqual(bp.decisions[0].id, "db")
        self.assertEqual(bp.decisions[0].status, "accepted")

        self.assertEqual(len(bp.questions), 1)
        self.assertEqual(bp.questions[0].id, "payment")
        self.assertEqual(len(bp.questions[0].options), 2)
        self.assertEqual(bp.questions[0].options[0].id, "stripe")

        task_spec = bp.tasks[0].spec()
        self.assertEqual(task_spec["budget_tokens"], 5000)
        self.assertEqual(task_spec["budget_seconds"], 120)

    def test_worker_proofs_extraction(self):
        ctx = tools.Context("shop", "folder", task="API")
        ctx.checks.append({
            "check": "pytest",
            "entry": "tests/test_api.py",
            "exit_code": 0,
            "output": "1 passed in 0.05s",
        })
        ctx.written.append("src/main.py")

        proofs = worker.proofs(ctx)
        self.assertEqual(len(proofs), 2)
        self.assertEqual(proofs[0]["command"], "pytest tests/test_api.py")
        self.assertTrue(proofs[0]["verified"])
        self.assertEqual(proofs[1]["command"], "test -f src/main.py")
        self.assertTrue(proofs[1]["verified"])

    @patch("agenti.agency.service.client.call", new_callable=AsyncMock)
    async def test_service_answer(self, mock_call):
        mock_call.return_value = {"ok": True}
        res = await service.answer("shop", "payment", "stripe", "Stripe selected")
        self.assertEqual(res, {"ok": True})
        mock_call.assert_awaited_once_with(
            "project_answer",
            id="shop",
            question="payment",
            option="stripe",
            answer="Stripe selected",
        )
