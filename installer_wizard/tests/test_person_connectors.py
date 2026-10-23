import importlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from access import require_admin
from features.people import api as people_api
from features.people import connectors
from features.telegram import api as telegram_api
from features.telegram import bot as telegram


def message(chat_id: int, text: str) -> dict:
    return {"message": {"chat": {"id": chat_id}, "text": text, "from": {"first_name": "Anna"}}}


class TelegramPerPersonTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = mock.patch.object(telegram, "DATA_FILE", Path(self.tmp.name) / "telegram.json")
        self.patch.start()
        self.bot = telegram.TelegramBot()
        self.bot.send = mock.AsyncMock()
        self.bound = []
        self.bot.handlers["bound"] = lambda slug, chat: self.bound.append((slug, chat))

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    async def pair(self, slug: str, chat_id: int) -> None:
        code = self.bot.new_pair_code(slug)["code"]
        await self.bot._handle(message(chat_id, code))

    async def test_code_binds_the_chat_to_the_person(self):
        await self.pair("anna", 11)
        self.assertEqual(self.bot.data["chats"]["11"]["person"], "anna")
        self.assertEqual(self.bound, [("anna", "11")])
        status = self.bot.person_status("anna")
        self.assertTrue(status["linked"])
        self.assertEqual([c["id"] for c in status["chats"]], ["11"])
        self.assertFalse(self.bot.person_status("marco")["linked"])

    async def test_code_without_person_stays_unbound(self):
        code = self.bot.new_pair_code()["code"]
        await self.bot._handle(message(12, code))
        self.assertNotIn("person", self.bot.data["chats"]["12"])
        self.assertEqual(self.bound, [])

    async def test_pending_code_is_shown_only_to_its_person(self):
        self.bot.new_pair_code("anna")
        self.assertIsNotNone(self.bot.person_status("anna")["pair_code"])
        self.assertIsNone(self.bot.person_status("marco")["pair_code"])

    async def test_wrong_code_does_not_pair(self):
        self.bot.new_pair_code("anna")
        await self.bot._handle(message(13, "000000x"))
        self.assertEqual(self.bot.data["chats"], {})

    async def test_unlink_removes_only_that_person(self):
        await self.pair("anna", 11)
        await self.pair("marco", 12)
        self.assertEqual(self.bot.unlink_person("anna"), 1)
        self.assertEqual(list(self.bot.data["chats"]), ["12"])
        self.assertEqual(self.bot.unlink_person(""), 0)

    async def test_notify_person_respects_the_chat_flag_and_target(self):
        await self.pair("anna", 11)
        await self.pair("marco", 12)
        self.bot.send.reset_mock()
        self.assertEqual(await self.bot.notify_person("anna", "ciao"), 1)
        self.bot.send.assert_awaited_once_with("11", "ciao")
        self.bot.update_chat("11", {"notify": False})
        self.assertEqual(await self.bot.notify_person("anna", "ciao"), 0)


class RegistryTest(unittest.TestCase):
    def test_real_connectors_are_registered(self):
        importlib.import_module("features.telegram.api")
        importlib.import_module("features.google.api")
        self.assertTrue({"telegram", "google"} <= set(connectors.known()))

    def test_a_failing_connector_does_not_break_the_listing(self):
        connectors.register("rotto", "Rotto", "x", lambda slug: 1 / 0)
        connectors.register("sano", "Sano", "x", lambda slug: {"available": True, "linked": True})
        try:
            rows = {r["id"]: r for r in connectors.listing("anna")}
        finally:
            connectors._registry.pop("rotto", None)
            connectors._registry.pop("sano", None)
        self.assertFalse(rows["rotto"]["available"])
        self.assertEqual(rows["rotto"]["error"], "ZeroDivisionError")
        self.assertTrue(rows["sano"]["linked"])


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = mock.patch.object(telegram, "DATA_FILE", Path(self.tmp.name) / "telegram.json")
        self.patch.start()
        telegram_api.bot.data = {"chats": {}}
        app = FastAPI()
        app.include_router(people_api.admin_routes)
        app.include_router(telegram_api.admin_routes)
        app.dependency_overrides[require_admin] = lambda: "admin"
        self.client = TestClient(app)

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_unknown_person_is_rejected_everywhere(self):
        with mock.patch.object(telegram_api.people, "load", return_value=None), mock.patch.object(people_api.people, "load", return_value=None):
            self.assertEqual(self.client.get("/api/people/nessuno/connectors").status_code, 404)
            self.assertEqual(self.client.post("/api/people/nessuno/telegram/pair-code").status_code, 404)
            self.assertEqual(self.client.delete("/api/people/nessuno/telegram").status_code, 404)

    def test_pairing_requires_the_bot_token(self):
        with mock.patch.object(telegram_api.people, "load", return_value={"slug": "anna"}), \
                mock.patch.object(type(telegram_api.bot), "token", new_callable=mock.PropertyMock, return_value=""):
            self.assertEqual(self.client.post("/api/people/anna/telegram/pair-code").status_code, 400)

    def test_pair_listing_toggle_and_unlink(self):
        bot = telegram_api.bot
        with mock.patch.object(telegram_api.people, "load", return_value={"slug": "anna"}), \
                mock.patch.object(telegram_api.people, "update") as update, \
                mock.patch.object(type(bot), "token", new_callable=mock.PropertyMock, return_value="t"):
            code = self.client.post("/api/people/anna/telegram/pair-code").json()
            self.assertEqual(len(code["code"]), 6)
            self.assertEqual(self.client.get("/api/people/anna/telegram").json()["pair_code"], code["code"])
            bot.data["chats"]["5"] = {"name": "Anna", "person": "anna", "notify": True, "voice": True}
            self.assertEqual(self.client.put("/api/people/anna/telegram/9", json={"notify": False}).status_code, 404)
            toggled = self.client.put("/api/people/anna/telegram/5", json={"notify": False, "role": "owner"}).json()
            self.assertFalse(toggled["chats"][0]["notify"])
            self.assertNotEqual(bot.data["chats"]["5"].get("role"), "owner")
            gone = self.client.delete("/api/people/anna/telegram").json()
            self.assertFalse(gone["linked"])
            update.assert_called_with("anna", {"telegram_id": ""})


class CredentialSettingsTest(unittest.TestCase):
    def test_credentials_can_be_saved_from_the_person_cards(self):
        import json
        base = Path(__file__).resolve().parents[1] / "features"
        wanted = {"telegram": {"NUXIVA_TELEGRAM_TOKEN"}, "google": {"NUXIVA_GOOGLE_CLIENT_ID", "NUXIVA_GOOGLE_CLIENT_SECRET"}}
        for feature, keys in wanted.items():
            manifest = json.loads((base / feature / "feature.json").read_text(encoding="utf-8"))
            declared = {item["key"]: item["type"] for item in manifest["settings"]}
            self.assertTrue(keys <= set(declared), feature)
            for key in keys:
                self.assertEqual(declared[key] == "secret", "SECRET" in key or "TOKEN" in key, key)
            for lang in ("it", "en", "fr"):
                labels = json.loads((base / feature / "language" / f"{lang}.json").read_text(encoding="utf-8")).get("settings", {})
                self.assertEqual(sorted(labels), sorted(declared), f"{feature}/{lang}")


if __name__ == "__main__":
    unittest.main()
