import asyncio
import unittest
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from access import require_admin
from features.brain import llm
from features.experts import routing
from features.projects import api as projects_api
from features.projects import director, management, model, service
from features.projects.model import ProjectError
from tests.test_projects import Isolated


def run(coro):
    return asyncio.run(coro)


class Script:

    def __init__(self, verdicts=None, finals=None):
        self.verdicts = list(verdicts or [])
        self.finals = list(finals or [])
        self.prompts = []

    async def __call__(self, prompt, **kw):
        self.prompts.append(prompt)
        if not kw.get("as_json"):
            return "risultato concreto"
        if "Il progetto soddisfa davvero" in prompt:
            return self.finals.pop(0) if self.finals else {"complete": True}
        if "Criteri di accettazione" in prompt:
            return self.verdicts.pop(0) if self.verdicts else {"verdict": "approve"}
        return {"steps": [{"text": "Progettare", "acceptance": "schema pronto"}, {"text": "Realizzare", "depends": [1]},
                          {"text": "Rifinire", "depends": [1]}]}


class Base(Isolated):

    def started(self, goal="Preparare il piano di studio di matematica"):
        project = service.start(goal, "it")
        self.script = Script()
        patches = [mock.patch.object(llm, "generate", self.script), mock.patch.object(management, "projects", self.store), mock.patch.object(routing, "best", return_value=None),
                   mock.patch("features.experts.autonomy.create_for", mock.AsyncMock(return_value=None))]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        run(service.plan(project))
        return project


class DirectorTests(Base):

    def test_plan_keeps_acceptance_and_dependencies(self):
        project = self.started()
        self.assertEqual(project.steps[0].acceptance, "schema pronto")
        self.assertEqual(project.steps[1].depends, ["s1"])
        self.assertEqual([s.id for s in service.ready(project)], ["s1"])

    def test_independent_steps_run_together_after_their_dependency(self):
        project = self.started()
        run(service.advance(project))
        self.assertEqual([s.status for s in project.steps], ["done", "pending", "pending"])
        self.assertEqual({s.id for s in service.ready(project)}, {"s2", "s3"})
        run(service.advance(project))
        self.assertEqual([s.status for s in project.steps], ["done", "done", "done"])

    def test_rejected_work_is_redone_with_the_ceo_feedback(self):
        project = self.started()
        self.script.verdicts = [{"verdict": "rework", "feedback": "manca lo schema delle tabelle"}]
        run(service.advance(project))
        first = project.steps[0]
        self.assertEqual((first.status, first.round), ("pending", 1))
        run(service.advance(project))
        self.assertTrue(any("Correggi esattamente questo: manca lo schema delle tabelle" in p for p in self.script.prompts))
        self.assertEqual(project.steps[0].status, "done")
        self.assertEqual(project.steps[0].feedback, "")

    def test_endless_rework_is_capped_and_marked_as_reserve(self):
        project = self.started()
        self.script.verdicts = [{"verdict": "rework", "feedback": "ancora no"}] * 5
        for _ in range(director.MAX_ROUNDS + 1):
            run(service.advance(project))
        self.assertEqual(project.steps[0].status, "done")
        self.assertIn("riserva", project.steps[0].error)

    def test_final_review_adds_missing_steps_then_closes(self):
        project = self.started()
        self.script.finals = [{"complete": False, "gaps": [{"text": "Aggiungere i test", "acceptance": "test verdi"}]}]
        for _ in range(6):
            run(service.advance(project))
        self.assertEqual(project.status, "done")
        self.assertIn("Aggiungere i test", [s.text for s in project.steps])
        self.assertTrue(all(s.status == "done" for s in project.steps))
        self.assertIn("potenziamento", [e["kind"] for e in project.log])

    def test_final_review_rounds_are_bounded(self):
        project = self.started()
        self.script.finals = [{"complete": False, "gaps": [{"text": f"Lacuna {i}", "acceptance": "x"}]} for i in range(10)]
        for _ in range(20):
            run(service.advance(project))
        self.assertEqual(project.status, "done")
        self.assertLessEqual(project.final_rounds, director.MAX_FINAL)

    def test_failed_execution_is_retried_then_reported(self):
        project = self.started()

        async def broken(step_project, step):
            raise ValueError("strumento rotto")

        with mock.patch.object(service, "execute", broken):
            run(service.advance(project))
            self.assertEqual((project.steps[0].status, project.steps[0].round), ("pending", 1))
            run(service.advance(project))
            run(service.advance(project))
            self.assertEqual(project.steps[0].status, "failed")
            run(service.advance(project))
        self.assertEqual(project.status, "failed")
        self.assertEqual([s.status for s in project.steps[1:]], ["failed", "failed"])

    def test_unreachable_model_keeps_the_review_for_later(self):
        project = self.started()

        async def down(prompt, tokens):
            raise llm.BrainUnavailable("offline")

        with mock.patch.object(director, "_ask", down):
            run(service.advance(project))
        self.assertEqual(project.steps[0].status, "review")
        run(service.advance(project))
        self.assertEqual(project.steps[0].status, "done")

    def test_coding_goals_get_a_development_workspace_name(self):
        project = self.started("Creare un sito PHP moderno con pagine separate")
        self.assertRegex(project.workspace, r"^[a-z][a-z0-9-]{1,39}$")
        self.assertIn(project.workspace, service.brief(project, project.steps[0]))
        self.assertEqual(self.started("Organizzare la ristrutturazione del bagno").workspace, "")

    def test_new_fields_survive_a_restart(self):
        project = self.started("Creare un sito PHP moderno con pagine separate")
        management.direct(project.id, "usa solo componenti accessibili")
        again = model.restore(project.to_dict())
        self.assertEqual(again.workspace, project.workspace)
        self.assertEqual(again.steps[1].depends, ["s1"])
        self.assertEqual(again.directives, ["usa solo componenti accessibili"])
        self.assertTrue(again.log)


class ManagementTests(Base):

    def test_owner_can_direct_add_remove_and_redo(self):
        project = self.started()
        management.direct(project.id, "tono formale")
        self.assertIn("tono formale", service.brief(project, project.steps[0]))
        management.add_step(project.id, "Preparare la presentazione", "slide pronte")
        self.assertEqual(project.steps[-1].id, "s4")
        management.remove_step(project.id, "s3")
        self.assertNotIn("s3", [s.id for s in project.steps])
        for _ in range(4):
            run(service.advance(project))
        self.assertEqual(project.status, "done")
        management.redo(project.id, "s1", "più dettagli")
        self.assertEqual(project.status, "running")
        self.assertEqual({s.status for s in project.steps if s.id in ("s1", "s2")}, {"pending"})
        self.assertIn("più dettagli", service.brief(project, project.steps[0]))

    def test_removing_a_step_cleans_the_dependencies(self):
        project = self.started()
        management.remove_step(project.id, "s1")
        self.assertEqual([s.depends for s in project.steps], [[], []])

    def test_busy_and_unknown_steps_are_refused(self):
        project = self.started()
        project.steps[0].status = "running"
        with self.assertRaises(ProjectError):
            management.remove_step(project.id, "s1")
        with self.assertRaises(ProjectError):
            management.redo(project.id, "s9", "x")
        with self.assertRaises(ProjectError):
            management.direct(project.id, "")

    def test_limits_are_enforced(self):
        project = self.started()
        for i in range(model.MAX_DIRECTIVES):
            management.direct(project.id, f"indicazione {i}")
        with self.assertRaises(ProjectError):
            management.direct(project.id, "una di troppo")
        project.steps = [model.Step(f"s{i + 1}", f"passo {i}") for i in range(model.MAX_STEPS)]
        with self.assertRaises(ProjectError):
            management.add_step(project.id, "oltre il limite")

    def test_team_can_be_extended_when_a_specialist_is_created(self):
        project = self.started()
        expert = mock.Mock(id="grafico", role="Grafico")
        with mock.patch("features.experts.autonomy.create_for", mock.AsyncMock(return_value=expert)):
            self.assertEqual(run(management.add_expert(project.id, "logo e identità visiva"))["role"], "Grafico")
        with self.assertRaises(ProjectError):
            run(management.add_expert(project.id, "qualcosa"))


class ApiTests(Base):

    def setUp(self):
        super().setUp()
        app = FastAPI()
        app.include_router(projects_api.admin_routes)
        app.dependency_overrides[require_admin] = lambda: "nunzio"
        self.client = TestClient(app)
        patcher = mock.patch.object(projects_api, "projects", self.store)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_endpoints_manage_the_project(self):
        project = self.started()
        base = f"/api/projects/{project.id}"
        self.assertEqual(self.client.post(f"{base}/directives", json={"text": "niente fronzoli"}).status_code, 200)
        added = self.client.post(f"{base}/steps", json={"text": "Controllare i risultati", "acceptance": "ok"})
        self.assertEqual(added.json()["steps"][-1]["acceptance"], "ok")
        self.assertEqual(self.client.delete(f"{base}/steps/s4").status_code, 200)
        self.assertEqual(self.client.post(f"{base}/steps/s1/redo", json={"feedback": "più chiaro"}).status_code, 200)
        self.assertEqual(self.client.delete(f"{base}/steps/s9").status_code, 400)
        self.assertEqual(self.client.post("/api/projects/xyz/directives", json={"text": "x"}).status_code, 404)
        self.assertEqual(self.client.post(f"{base}/steps", json={"text": ""}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
