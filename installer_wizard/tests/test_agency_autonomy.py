import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

import nuxiva_supervisor
from features.agency import api, autonomy, service
from features.agency.memory import ProjectMemory

HEADERS = {"X-Nuxiva-Request": "1"}


class AutonomyEngineTest(unittest.TestCase):
    def test_low_risk_task_auto_approved_with_proofs(self):
        task = {
            "id": "t-style",
            "title": "Aggiungi stili CSS e template HTML per la navbar",
            "role": "frontend",
            "acceptance": [{"text": "CSS responsive valido", "verified": True}],
        }
        proofs = [{"criterion": "CSS compiles", "verified": True}]
        decision = autonomy.evaluate(task, "navbar.css created", proofs, critic_approved=True)
        self.assertTrue(decision.approved)
        self.assertTrue(decision.autonomous)
        self.assertEqual(decision.risk, "low")
        self.assertGreaterEqual(decision.confidence, 0.95)
        self.assertFalse(decision.requires_double_permission)

    def test_medium_risk_task_auto_approved_when_verified(self):
        task = {
            "id": "t-endpoint",
            "title": "Crea controller e handler REST per i prodotti",
            "role": "backend",
            "acceptance": [{"text": "Endpoint 200 OK", "verified": True}],
        }
        proofs = [{"criterion": "Test test_products passes", "verified": True}]
        decision = autonomy.evaluate(task, "products.py implemented", proofs, critic_approved=True)
        self.assertTrue(decision.approved)
        self.assertTrue(decision.autonomous)
        self.assertEqual(decision.risk, "medium")

    def test_high_risk_task_holds_for_human_supervision(self):
        task = {
            "id": "t-migration",
            "title": "Esegui migration e schema alter table per gli ordini",
            "role": "backend",
            "acceptance": [{"text": "Schema aggiornato"}],
        }
        proofs = [{"criterion": "Migration applied", "verified": True}]
        decision = autonomy.evaluate(task, "schema altered", proofs, critic_approved=True)
        self.assertFalse(decision.approved)
        self.assertFalse(decision.autonomous)
        self.assertEqual(decision.risk, "high")
        self.assertIn("Revisione umana richiesta", decision.rationale)

    def test_critical_risk_task_requires_double_permission(self):
        task = {
            "id": "t-vault",
            "title": "Aggiorna password e secret token per le credenziali IBAN conto corrente",
            "role": "security",
            "acceptance": [{"text": "Credenziali salvate"}],
        }
        decision = autonomy.evaluate(task, "secret stored", [], critic_approved=True)
        self.assertFalse(decision.approved)
        self.assertFalse(decision.autonomous)
        self.assertEqual(decision.risk, "critical")
        self.assertTrue(decision.requires_double_permission)
        self.assertFalse(decision.reversible)

    def test_critic_rejection_lowers_confidence_and_prevents_approval(self):
        task = {
            "id": "t-doc",
            "title": "Scrivi documentazione README",
            "role": "architect",
        }
        decision = autonomy.evaluate(task, "readme draft", [], critic_approved=False)
        self.assertFalse(decision.approved)
        self.assertFalse(decision.autonomous)
        self.assertLess(decision.confidence, 0.70)

    def test_enrich_task_kanban(self):
        item = {"id": "t1", "title": "Crea form di login e password utente", "role": "frontend"}
        enriched = autonomy.enrich_task_kanban(item)
        self.assertEqual(enriched["risk"], "critical")
        self.assertTrue(enriched["requires_double_permission"])
        self.assertIn("confidence", enriched)


class AutonomyApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.web = TestClient(nuxiva_supervisor.public)

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        memory = ProjectMemory(self.tmp / "state")
        memory.save("proj1", {"blueprint": {"summary": "P"}, "reasoning": {}})
        patcher_mem = mock.patch.object(service, "memory", memory)
        patcher_auth = mock.patch.object(api, "require_display", lambda request: None)
        patcher_mem.start()
        patcher_auth.start()
        self.addCleanup(patcher_mem.stop)
        self.addCleanup(patcher_auth.stop)

    def test_autonomy_endpoint_returns_evaluations(self):
        fake_detail = {
            "project": {"id": "proj1", "title": "Progetto"},
            "tasks": [
                {"id": "t-css", "title": "Stili css responsive", "role": "frontend", "status": "done"},
                {"id": "t-sec", "title": "Salva password e api_key segreta", "role": "security", "status": "review"},
            ],
        }
        with mock.patch.object(service, "detail", mock.AsyncMock(return_value=fake_detail)):
            res = self.web.get("/api/agency/board/proj1/autonomy", headers=HEADERS)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["engine"], "jarvis_risk_matrix")
        self.assertEqual(len(data["evaluations"]), 2)
        self.assertEqual(data["auto_approved"], 1)
        self.assertEqual(data["human_supervision_required"], 1)


if __name__ == "__main__":
    unittest.main()
