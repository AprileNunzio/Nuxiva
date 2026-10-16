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

        import asyncio
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

        import asyncio
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

    def test_chat_commands(self):
        import asyncio
        reply, _ = asyncio.run(commands.answer("avvia un progetto per riordinare la cantina"))
        self.assertIn("avviato", reply)
        reply, _ = asyncio.run(commands.answer("a che punto sono i progetti"))
        self.assertIn("riordinare", reply.lower())
        with self.assertRaises(LookupError):
            asyncio.run(commands.answer("che ore sono"))


if __name__ == "__main__":
    unittest.main()
