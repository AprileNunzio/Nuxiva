import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from features.games import api, saves

GAME = {"v": 1, "moves": [[6, 4, 4, 4, ""], [1, 4, 3, 4, ""]], "player": "white"}
HEAD = {"X-Nuxiva-Request": "1"}


class SavesTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        for patcher in (mock.patch.object(saves, "FOLDER", base / "games"), mock.patch.object(saves, "KEY_FILE", base / "k.key"),
                        mock.patch("features.people.people.load", return_value={"slug": "anna"})):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_create_update_list_remove(self):
        row = saves.put("anna", "new", {"save": GAME, "over": False}, now=100)
        self.assertEqual((row["moves"], row["turn"]), (2, "white"))
        saves.put("anna", row["id"], {"save": {**GAME, "moves": GAME["moves"] + [[7, 6, 5, 5, ""]]}}, now=200)
        listing = saves.listing("anna")
        self.assertEqual(len(listing), 1)
        self.assertEqual((listing[0]["moves"], listing[0]["turn"], listing[0]["created"]), (3, "black", 100))
        self.assertEqual(saves.get("anna", row["id"])["save"]["moves"][2], [7, 6, 5, 5, ""])
        self.assertTrue(saves.remove("anna", row["id"]))
        self.assertEqual(saves.listing("anna"), [])

    def test_invalid_games_are_rejected(self):
        for bad in ({}, {"v": 2}, {**GAME, "player": "red"}, {**GAME, "moves": [[8, 0, 0, 0, ""]]},
                    {**GAME, "moves": [[0, 0, 0, 0, "king"]]}, {**GAME, "moves": [[0, 0, 0]]}, {**GAME, "moves": [[0] * 5] * 601},
                    {**GAME, "moves": [[True, 0, 0, 0, ""]]}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                saves.put("anna", "new", {"save": bad})

    def test_keeps_only_the_latest_twenty(self):
        for i in range(25):
            saves.put("anna", "new", {"save": GAME}, now=1000 + i)
        listing = saves.listing("anna")
        self.assertEqual(len(listing), saves.MAX_SAVES)
        self.assertEqual(listing[0]["updated"], 1024)

    def test_stored_sealed_on_disk(self):
        saves.put("anna", "new", {"save": GAME})
        raw = next(saves.FOLDER.glob("*.chess")).read_bytes()
        self.assertNotIn(b"moves", raw)


class ApiTest(unittest.TestCase):
    def setUp(self):
        SavesTest.setUp(self)
        app = FastAPI()
        app.include_router(api.public_routes)
        self.client = TestClient(app)
        patch = mock.patch.object(api, "require_display", lambda request: None)
        patch.start()
        self.addCleanup(patch.stop)

    def test_round_trip(self):
        created = self.client.put("/api/games/chess/anna/new", json={"save": GAME}, headers=HEAD)
        self.assertEqual(created.status_code, 200)
        save_id = created.json()["id"]
        self.assertEqual(len(self.client.get("/api/games/chess/anna").json()["saves"]), 1)
        self.assertEqual(self.client.get(f"/api/games/chess/anna/{save_id}").json()["save"], GAME)
        self.assertEqual(self.client.delete(f"/api/games/chess/anna/{save_id}", headers=HEAD).status_code, 200)
        self.assertEqual(self.client.get(f"/api/games/chess/anna/{save_id}").status_code, 404)

    def test_writes_need_the_request_header_and_valid_ids(self):
        self.assertEqual(self.client.put("/api/games/chess/anna/new", json={"save": GAME}).status_code, 403)
        self.assertEqual(self.client.get("/api/games/chess/anna/..%2Fx").status_code, 404)
        self.assertEqual(self.client.put("/api/games/chess/anna/new", json={"save": {"v": 1}}, headers=HEAD).status_code, 400)
        self.assertEqual(self.client.put("/api/games/chess/anna/new", content=b"x" * 30000, headers=HEAD).status_code, 413)
