import asyncio
import unittest
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from features.agency import commands, presence, service
from features.agency.client import AgencyUnavailable
from features.tasks import api as tasks_api
from features.tasks import sources


def card(pid, status, percent=50):
    return {"id": pid, "title": f"Progetto {pid}", "status": status, "percent": percent, "created_at_ms": 4_000_000_000_000,
            "counts": {"total": 4, "done": 2, "pending": 1, "running": 1, "review": 0, "failed": 0, "cancelled": 0, "blocked": 0}}


class CommandsTest(unittest.TestCase):
    def run_answer(self, text):
        return asyncio.run(commands.answer(text))

    def test_builds_start_the_agency_in_the_speaker_language(self):
        for text, lang in (("creami un sito con 100 pagine", "it"), ("sviluppa una piattaforma gestionale", "it"),
                           ("build me a website for my bakery", "en"), ("créame una aplicación para el gimnasio", "es"),
                           ("crée-moi un site pour la boulangerie", "fr")):
            with self.subTest(text=text), mock.patch.object(commands, "background") as queued, \
                    mock.patch.object(service, "launch", mock.MagicMock()) as launch:
                speech, ui = self.run_answer(text)
                queued.assert_called_once()
                launch.assert_called_once_with(text, lang)
                self.assertEqual((ui["mode"], ui["agency"]["view"]), ("face", "galaxy"))
                self.assertIn("09 Progetti", speech)

    def test_unrelated_requests_are_left_to_other_connectors(self):
        for text in ("crea una canzone blues", "che tempo fa", "x" * 3000):
            with self.subTest(text=text[:20]), self.assertRaises(LookupError):
                self.run_answer(text)

    def test_status_lists_active_projects(self):
        overview = {"projects": [card("a", "running"), card("b", "completed", 100)], "agents": {}, "tools": 0}
        with mock.patch.object(commands.board, "overview", mock.AsyncMock(return_value=overview)):
            speech, _ = self.run_answer("a che punto sono i progetti?")
        self.assertIn("Progetto a", speech)
        self.assertNotIn("Progetto b", speech)

    def test_status_when_engine_is_down(self):
        with mock.patch.object(commands.board, "overview", mock.AsyncMock(side_effect=AgencyUnavailable("x"))):
            speech, _ = self.run_answer("how is the project progress?")
        self.assertIn("not reachable", speech)


class DisplayViewTest(unittest.TestCase):
    OVERVIEW = {"projects": [card("shop", "running"), card("pizza", "paused")], "agents": {}, "tools": 0}

    def setUp(self):
        self.intent = presence.DisplayIntent()
        for patcher in (mock.patch.object(commands, "intent", self.intent),
                        mock.patch.object(commands.board, "overview", mock.AsyncMock(return_value=self.OVERVIEW))):
            patcher.start()
            self.addCleanup(patcher.stop)

    def say(self, text):
        return asyncio.run(commands.answer(text))

    def test_voice_drives_the_display_from_any_device(self):
        speech, ui = self.say("mostrami i progetti")
        self.assertEqual(ui["agency"]["view"], "galaxy")
        speech, ui = self.say("apri il progetto pizza")
        self.assertEqual((ui["agency"]["view"], ui["agency"]["id"]), ("project", "pizza"))
        self.assertIn("Progetto pizza", speech)
        speech, ui = self.say("close the projects")
        self.assertEqual(ui["agency"]["view"], "close")
        self.assertEqual(self.intent.current()["seq"], 3)
        speech, ui = self.say("a che punto sono i progetti")
        self.assertNotIn("agency", ui)

    def test_unknown_project_falls_back_to_the_galaxy(self):
        speech, ui = self.say("apri il progetto astronave")
        self.assertEqual(ui["agency"]["view"], "galaxy")
        self.assertIn("Non trovo", speech)

    def test_intents_expire(self):
        self.intent.push("galaxy")
        with mock.patch.object(presence.time, "time", return_value=presence.time.time() + presence.TTL_SECONDS + 1):
            self.assertIsNone(self.intent.current())
        with self.assertRaises(ValueError):
            self.intent.push("explode")

    def test_snapshot_carries_the_intent(self):
        import snapshot
        with mock.patch.object(snapshot, "agency_intent", self.intent):
            self.intent.push("project", "shop")
            self.assertEqual(snapshot.full_snapshot(False)["agency"]["id"], "shop")


class TaskCenterTest(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.dependency_overrides[tasks_api.require_admin] = lambda: "admin"
        app.include_router(tasks_api.admin_routes)
        self.client = TestClient(app)

    def test_projects_appear_as_tasks_and_can_be_cancelled(self):
        overview = {"projects": [card("shop", "running"), card("old", "failed")]}
        with mock.patch.object(sources.board, "overview", mock.AsyncMock(return_value=overview)):
            rows = [t for t in self.client.get("/api/tasks").json()["tasks"] if t["feature"] == "agency"]
        self.assertEqual([(r["id"], r["state"], r["progress"]) for r in rows], [("agency:shop", "running", 0.5), ("agency:old", "error", 0.5)])
        with mock.patch.object(service, "control", mock.AsyncMock(return_value={})) as control:
            self.assertEqual(self.client.post("/api/tasks/agency:shop/cancel").status_code, 200)
        control.assert_awaited_once_with("shop", "cancel")
        self.assertEqual(self.client.post("/api/tasks/agency:..%2Fx/cancel").status_code, 404)

    def test_engine_down_leaves_the_task_center_working(self):
        with mock.patch.object(sources.board, "overview", mock.AsyncMock(side_effect=AgencyUnavailable("x"))):
            self.assertEqual(self.client.get("/api/tasks").status_code, 200)


if __name__ == "__main__":
    unittest.main()
