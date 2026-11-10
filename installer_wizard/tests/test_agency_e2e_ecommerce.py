import tempfile
import unittest
from pathlib import Path
from unittest import mock

from features.agency import blueprint, client as client_module, runner, service, tools, worker
from features.agency.memory import ProjectMemory
from features.shares import archive


class FakeEcommerceAgencyDaemon:
    def __init__(self) -> None:
        self.revoked_workers: set[str] = set()
        self.checkpoints: dict[str, str] = {}
        self.answers: dict[str, str] = {}
        self.project_state = {
            "project": {
                "id": "ecom-1",
                "title": "E-Commerce Informatica",
                "status": "running",
            },
            "decisions": [
                {
                    "id": "dec-db",
                    "title": "Database Engine",
                    "rationale": "PostgreSQL with connection pooling",
                    "status": "accepted",
                }
            ],
            "questions": [
                {
                    "id": "q-pay",
                    "prompt": "Quale gateway di pagamento integrare primariamente?",
                    "options": [
                        {"id": "stripe", "label": "Stripe", "description": "Carta e wallet"},
                        {"id": "paypal", "label": "PayPal", "description": "Conto e rateale"},
                    ],
                }
            ],
            "tasks": [
                {
                    "id": "t-catalog",
                    "title": "Catalogo e ricerca componenti PC",
                    "status": "in_progress",
                    "budget_tokens": 8000,
                    "budget_seconds": 180,
                    "feedback": None,
                    "checkpoint": None,
                },
                {
                    "id": "t-cart",
                    "title": "Carrello e checkout",
                    "status": "pending",
                    "budget_tokens": 5000,
                    "budget_seconds": 120,
                    "feedback": None,
                    "checkpoint": None,
                },
            ],
            "folder": "ecommerce",
        }

    async def call(self, op: str, **fields):
        if op == "project_get":
            return self.project_state
        if op == "project_answer":
            qid = fields["question"]
            ans = fields.get("answer") or fields.get("option", "")
            self.answers[qid] = ans
            self.project_state["questions"] = [
                q for q in self.project_state["questions"] if q["id"] != qid
            ]
            return {"ok": True, "remaining_questions": len(self.project_state["questions"])}
        if op == "task_update":
            w = fields.get("worker")
            if w and w in self.revoked_workers:
                raise client_module.AgencyRejected("revoked", "worker assignment revoked")
            tid = fields["task"]
            act = fields["action"]
            task = next(t for t in self.project_state["tasks"] if t["id"] == tid)
            if act == "submit":
                chk = fields.get("checkpoint", "")
                self.checkpoints[tid] = chk
                task["status"] = "review"
                task["checkpoint"] = chk
            elif act == "approve":
                task["status"] = "done"
            elif act == "cancel":
                task["status"] = "cancelled"
            return self.project_state
        if op == "project_control":
            act = fields["action"]
            if act == "cancel":
                self.project_state["project"]["status"] = "cancelled"
                for t in self.project_state["tasks"]:
                    if t["status"] in ("pending", "in_progress"):
                        t["status"] = "cancelled"
            elif act == "pause":
                self.project_state["project"]["status"] = "paused"
            elif act == "resume":
                self.project_state["project"]["status"] = "running"
            return self.project_state
        if op == "assignment_revoke":
            w = fields.get("worker", "worker-1")
            self.revoked_workers.add(w)
            return {"ok": True}
        raise NotImplementedError(op)


class EcommerceDeliveryEndToEndTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.condivisa = self.tmp / "condivisa"
        self.progetti = self.condivisa / "09 Progetti"
        self.project_dir = self.progetti / "ecommerce"
        self.project_dir.mkdir(parents=True, exist_ok=True)

        self.fake_daemon = FakeEcommerceAgencyDaemon()
        self.memory = ProjectMemory(self.tmp / "state")

        self.patches = [
            mock.patch.object(archive, "ROOT", self.condivisa),
            mock.patch.object(runner, "client", self.fake_daemon),
            mock.patch.object(tools, "client", self.fake_daemon),
            mock.patch.object(service, "client", self.fake_daemon),
            mock.patch.object(runner, "memory", self.memory),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    async def test_complete_ecommerce_delivery_flow(self) -> None:
        raw_plan = {
            "title": "E-Commerce Informatica",
            "summary": "Piattaforma di vendita hardware e periferiche con gestione ordini",
            "architecture": "Rust backend e Svelte frontend",
            "roles": [
                {"id": "architect", "mission": "Progettazione database e architettura"},
                {"id": "backend", "mission": "Sviluppo API catalogo e checkout"},
            ],
            "decisions": [
                {
                    "id": "dec-db",
                    "title": "Database Engine",
                    "rationale": "PostgreSQL with connection pooling",
                    "status": "accepted",
                }
            ],
            "questions": [
                {
                    "id": "q-pay",
                    "prompt": "Quale gateway di pagamento integrare primariamente?",
                    "options": [
                        {"id": "stripe", "label": "Stripe", "description": "Carta e wallet"},
                        {"id": "paypal", "label": "PayPal", "description": "Conto e rateale"},
                    ],
                }
            ],
            "tasks": [
                {
                    "id": "t-catalog",
                    "title": "Catalogo e ricerca componenti PC",
                    "role": "backend",
                    "estimate_seconds": 600,
                    "budget_tokens": 8000,
                    "budget_seconds": 180,
                    "acceptance": ["Modelli di prodotto validati", "Test catalogo passano"],
                },
                {
                    "id": "t-cart",
                    "title": "Carrello e checkout",
                    "role": "backend",
                    "estimate_seconds": 400,
                    "budget_tokens": 5000,
                    "budget_seconds": 120,
                    "acceptance": ["Calcolo totale con IVA", "Test checkout passano"],
                },
            ],
        }
        parsed = blueprint.parse(raw_plan, "E-Commerce Informatica")
        self.assertEqual(len(parsed.decisions), 1)
        self.assertEqual(parsed.decisions[0].id, "dec-db")
        self.assertEqual(len(parsed.questions), 1)

        ans_res = await service.answer("ecom-1", "q-pay", "stripe", "Stripe")
        self.assertTrue(ans_res["ok"])
        self.assertEqual(self.fake_daemon.answers.get("q-pay"), "Stripe")

        ctx = tools.Context(
            project_id="ecom-1",
            folder="ecommerce",
            task="t-catalog",
            worker="w-catalog-1",
            generation=1,
            permissions=["read", "write", "execute"],
        )
        write_res = await tools.call(
            ctx,
            "write_file",
            {"path": "src/catalog.py", "content": "def list_products(): return ['cpu', 'gpu']"},
        )
        self.assertIn("src/catalog.py", write_res)
        self.assertTrue((self.project_dir / "src/catalog.py").exists())

        ctx.checks.append({
            "check": "python_tests",
            "entry": "tests/test_catalog.py",
            "exit_code": 0,
            "output": "Catalog verification OK",
        })
        proof_items = worker.proofs(ctx)
        self.assertEqual(len(proof_items), 2)
        self.assertTrue(all(p["verified"] for p in proof_items))

        submit_res = await self.fake_daemon.call(
            "task_update",
            project="ecom-1",
            task="t-catalog",
            action="submit",
            worker="w-catalog-1",
            generation=1,
            checkpoint="sha256-artifact-hash-catalog-v1",
        )
        t_cat = next(t for t in submit_res["tasks"] if t["id"] == "t-catalog")
        self.assertEqual(t_cat["status"], "review")
        self.assertEqual(t_cat["checkpoint"], "sha256-artifact-hash-catalog-v1")

        state_after_restart = await self.fake_daemon.call("project_get", id="ecom-1")
        restarted_task = next(t for t in state_after_restart["tasks"] if t["id"] == "t-catalog")
        self.assertEqual(restarted_task["status"], "review")
        self.assertEqual(restarted_task["checkpoint"], "sha256-artifact-hash-catalog-v1")

        approved_res = await self.fake_daemon.call(
            "task_update",
            project="ecom-1",
            task="t-catalog",
            action="approve",
        )
        self.assertEqual(
            next(t for t in approved_res["tasks"] if t["id"] == "t-catalog")["status"],
            "done",
        )

        cancel_res = await self.fake_daemon.call(
            "project_control",
            project="ecom-1",
            action="cancel",
        )
        self.assertEqual(cancel_res["project"]["status"], "cancelled")
        t_cart = next(t for t in cancel_res["tasks"] if t["id"] == "t-cart")
        self.assertEqual(t_cart["status"], "cancelled")


if __name__ == "__main__":
    unittest.main()
