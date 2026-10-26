import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from features.brain import llm
from features.experts import routing
from features.projects import commands, model, service, store as store_module
from features.projects.model import ProjectError


class Isolated(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = store_module.ProjectStore()
        patches = [mock.patch.object(store_module, "FILE", Path(self.dir.name) / "projects.json"),
                   mock.patch.object(service, "projects", self.store),
                   mock.patch.object(commands, "projects", self.store),
                   mock.patch.object(service.publish, "push"), mock.patch.object(service.publish, "drop")]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.dir.cleanup)


class ProjectTest(Isolated):
    def test_goal_validation_and_persistence(self):
        with self.assertRaises(ProjectError):
            service.start("corto", "it")
        project = service.start("Organizzare la ristrutturazione del bagno", "it")
        self.assertEqual(project.status, "planning")
        again = store_module.ProjectStore()
        self.assertEqual(again.get(project.id).goal, project.goal)

    def test_plan_then_steps_run_to_done(self):
        project = service.start("Preparare il piano di studio di matematica", "it")

        async def fake(prompt, **kw):
            return {"steps": [{"text": "Raccogliere argomenti"}, {"text": "Fissare le scadenze"}]} if kw.get("as_json") else "fatto"

        with mock.patch.object(llm, "generate", fake), mock.patch.object(routing, "best", return_value=None):
            asyncio.run(service.plan(project))
            self.assertEqual(project.status, "running")
            self.assertEqual(len(project.steps), 2)
            for _ in range(3):
                asyncio.run(service.advance(project))
        self.assertEqual(project.status, "done")
        self.assertEqual(project.progress, 100)

    def test_brain_unavailable_keeps_planning(self):
        project = service.start("Costruire una libreria su misura", "it")

        async def down(prompt, **kw):
            raise llm.BrainUnavailable("nessun modello")

        with mock.patch.object(llm, "generate", down):
            asyncio.run(service.plan(project))
        self.assertEqual(project.status, "planning")
        self.assertTrue(project.error)

    def test_pause_resume_cancel(self):
        project = service.start("Riorganizzare l'archivio dei documenti", "it")
        service.pause(project.id)
        self.assertEqual(project.status, "paused")
        service.resume(project.id)
        self.assertEqual(project.status, "planning")
        service.cancel(project.id)
        with self.assertRaises(ProjectError):
            service.pause(project.id)

    def test_running_step_restored_as_pending(self):
        project = service.start("Imparare le basi della chitarra", "it")
        project.steps = model.steps_from([{"text": "Accordare lo strumento"}])
        project.steps[0].status = "running"
        self.store.save(project)
        self.assertEqual(store_module.ProjectStore().get(project.id).steps[0].status, "pending")

    def test_3d_project_models_first_and_opens_the_studio(self):
        from features.models3d import studio
        plain = service.start("Organizzare la ristrutturazione del bagno", "it")
        project = service.start("Progetta un portapenne in 3D da stampare", "it")
        self.assertEqual((plain.kind, project.kind), ("general", "3d"))

        async def fake(prompt, **kw):
            return {"steps": [{"text": "Scegliere le misure"}, {"text": "Preparare il file per la stampa"}]}

        async def create(subject):
            return {"id": "portapenne-abc123", "title": "Portapenne", "parts": [{}, {}]}

        with mock.patch.object(llm, "generate", fake), mock.patch.object(routing, "best", return_value=None), \
                mock.patch("features.models3d.generator.create", create), mock.patch.object(studio, "open_studio") as opened:
            asyncio.run(service.plan(project))
            self.assertEqual([s.action for s in project.steps], ["model3d", "", ""])
            self.assertEqual([s.id for s in project.steps], ["s1", "s2", "s3"])
            asyncio.run(service.advance(project))
        opened.assert_called_once()
        self.assertEqual(project.model_id, "portapenne-abc123")
        self.assertEqual(project.steps[0].status, "done")
        self.assertEqual(store_module.ProjectStore().get(project.id).kind, "3d")

    def test_display_controls_pause_resume_and_reject_unknown(self):
        from fastapi import HTTPException
        from features.projects import api
        project = service.start("Imparare le basi della chitarra", "it")
        request = mock.Mock()
        with mock.patch.object(api, "require_display"), mock.patch.object(api, "projects", self.store):
            asyncio.run(api.display_control(project.id, "pause", request))
            self.assertEqual(project.status, "paused")
            asyncio.run(api.display_control(project.id, "resume", request))
            self.assertEqual(project.status, "planning")
            with self.assertRaises(HTTPException) as unknown:
                asyncio.run(api.display_control(project.id, "delete", request))
            self.assertEqual(unknown.exception.status_code, 404)
            with self.assertRaises(HTTPException) as missing:
                asyncio.run(api.display_control("pdeadbeef00", "pause", request))
            self.assertEqual(missing.exception.status_code, 404)

    def test_chat_commands(self):
        reply, _ = asyncio.run(commands.answer("avvia un progetto per riordinare la cantina"))
        self.assertIn("avviato", reply)
        reply, _ = asyncio.run(commands.answer("a che punto sono i progetti"))
        self.assertIn("riordinare", reply.lower())
        with self.assertRaises(LookupError):
            asyncio.run(commands.answer("che ore sono"))


if __name__ == "__main__":
    unittest.main()
