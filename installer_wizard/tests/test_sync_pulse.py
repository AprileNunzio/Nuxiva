import asyncio
import json
import unittest
from pathlib import Path
from unittest import mock

from agenti.desktop.sources import SOURCES
from agenti.google.errors import GoogleApiError
from agenti.people import focus, sync_view
from agenti.people.sync_board import SyncBoard, board

WIDGET = Path(__file__).resolve().parents[1] / "widgets" / "sync_pulse"


class BoardTest(unittest.TestCase):
    def test_states_and_reasons(self):
        b = SyncBoard()
        b.start("ana", "google_gmail", 100.0)
        self.assertEqual(b.rows("ana", 101.0)[0]["state"], "running")
        b.ok("ana", "google_gmail", 102.0)
        self.assertEqual(b.rows("ana", 110.0)[0]["state"], "ok")
        b.fail("ana", "google_tasks", "Google:\n  boom " + "x" * 400, 111.0, reason="scope_missing<script>")
        row = next(r for r in b.rows("ana", 112.0) if r["key"] == "google_tasks")
        self.assertEqual(row["state"], "error")
        self.assertEqual(row["reason"], "scope_missingscript")
        self.assertLessEqual(len(row["error"]), 140)
        self.assertNotIn("\n", row["error"])

    def test_timeout_and_stale(self):
        b = SyncBoard()
        b.start("ana", "google", 100.0)
        self.assertEqual(b.rows("ana", 300.0)[0]["reason"], "timeout")
        b.ok("ana", "google", 300.0)
        self.assertEqual(b.rows("ana", 300.0 + 901)[0:], [])
        b.fail("ana", "google", "x", 300.0)
        self.assertEqual(len(b.rows("ana", 5000.0)), 1)

    def test_off_and_forget(self):
        b = SyncBoard()
        b.ok("ana", "google_tasks", 1.0)
        b.off("ana", "google_tasks")
        self.assertEqual(b.rows("ana", 2.0), [])
        b.ok("ana", "google", 1.0)
        b.forget("ana")
        self.assertEqual(b.rows("ana", 2.0), [])


class ViewTest(unittest.TestCase):
    def setUp(self):
        board.forget("ana")
        self.addCleanup(board.forget, "ana")

    def _build(self, listing, devices=(), now=1000.0):
        with mock.patch.object(sync_view.connectors, "listing", return_value=listing), \
             mock.patch.object(sync_view.service, "devices_view", return_value=list(devices)), \
             mock.patch.object(sync_view.service, "current", return_value={}):
            return sync_view.build("ana", now)

    def test_nothing_linked(self):
        self.assertIsNone(self._build([{"id": "google", "linked": False}, {"id": "telegram", "linked": False}]))

    def test_google_waits_for_first_sync_then_shows_steps(self):
        view = self._build([{"id": "google", "linked": True}])
        self.assertEqual(view["phase"], "running")
        self.assertEqual(view["rows"][0]["key"], "google")
        board.ok("ana", "google", 999.0)
        board.fail("ana", "google_gmail", "Gmail API off", 999.0, reason="api_disabled")
        view = self._build([{"id": "google", "linked": True}])
        self.assertEqual(view["phase"], "error")
        self.assertEqual(view["rows"][0]["key"], "google_gmail")
        self.assertEqual(view["errors"], 1)
        self.assertEqual(view["done"], 1)

    def test_revoked_google_and_telegram_status(self):
        view = self._build([{"id": "google", "linked": True, "revoked": True},
                            {"id": "telegram", "linked": True, "available": True, "status": "errore: rete"}])
        self.assertEqual({r["key"]: r["reason"] for r in view["rows"]}, {"google": "revoked", "telegram": ""})
        self.assertEqual(next(r for r in view["rows"] if r["key"] == "telegram")["error"], "rete")
        view = self._build([{"id": "telegram", "linked": True, "available": True, "status": "attivo"}])
        self.assertEqual(view["phase"], "ok")

    def test_devices_and_health(self):
        board.ok("ana", "google_health", 990.0)
        view = self._build([{"id": "vitals", "linked": True}],
                           [{"kind": "ble", "label": "Mi Band", "state": "streaming", "last": 995.0},
                            {"kind": "phone", "label": "Pixel", "state": "waiting"},
                            {"kind": "ble", "label": "Vecchio", "state": "off"},
                            {"kind": "ble", "label": "Strano", "state": "unsupported"}])
        keys = [(r["key"], r["state"], r["name"]) for r in view["rows"]]
        self.assertEqual(keys[0], ("band", "error", "Strano"))
        self.assertIn(("phone", "waiting", "Pixel"), keys)
        self.assertIn(("google_health", "ok", ""), keys)
        self.assertNotIn("Vecchio", [r["name"] for r in view["rows"]])


class CardTest(unittest.TestCase):
    def test_source_registered_and_privacy(self):
        self.assertIn("person_sync", SOURCES)
        with mock.patch.object(focus, "_away", return_value=True):
            self.assertIsNone(focus.sync_card())

    def test_card_has_person(self):
        with mock.patch.object(focus, "_focus", return_value="ana"), \
             mock.patch.object(focus, "_who", return_value={"slug": "ana", "name": "Ana Rossi", "initials": "AR"}), \
             mock.patch.object(focus, "_kick"), \
             mock.patch.object(sync_view, "build", return_value={"phase": "ok", "rows": [], "total": 0, "done": 0, "errors": 0}):
            self.assertEqual(focus.sync_card()["person"]["name"], "Ana Rossi")


class RefreshTest(unittest.TestCase):
    def test_one_failing_step_does_not_stop_the_others(self):
        from agenti.google import gservices
        board.forget("ana")
        self.addCleanup(board.forget, "ana")
        session = mock.Mock()
        session.info = {"refresh": "r"}
        session.ready.side_effect = lambda s: s in ("gmail", "tasks")
        with mock.patch.object(gservices.google, "for_profile", return_value=session), \
             mock.patch.object(gservices.notifier, "brief", mock.AsyncMock()), \
             mock.patch.object(gservices.notifier, "mail", mock.AsyncMock(side_effect=GoogleApiError(403, "api_disabled", "off"))), \
             mock.patch.object(gservices.notifier, "tasks", mock.AsyncMock()) as tasks:
            asyncio.run(gservices.google._refresh({"slug": "ana"}, 0))
        tasks.assert_awaited_once()
        rows = {r["key"]: r for r in board.rows("ana")}
        self.assertEqual(rows["google_gmail"]["reason"], "api_disabled")
        self.assertEqual(rows["google_tasks"]["state"], "ok")
        self.assertNotIn("google_calendar", rows)
        self.assertTrue(session.status.startswith("errore"))


class WidgetFilesTest(unittest.TestCase):
    def test_manifest_and_languages(self):
        manifest = json.loads((WIDGET / "widget.json").read_text(encoding="utf-8"))
        self.assertEqual((manifest["bind"], manifest["screen_role"], manifest["personal"], manifest["chrome"]), ("person_sync", "person", True, False))
        keys = None
        for lang in ("it", "en", "es", "fr"):
            words = json.loads((WIDGET / "language" / f"{lang}.json").read_text(encoding="utf-8"))["dictionary"]
            keys = keys or set(words)
            self.assertEqual(set(words), keys, lang)
        self.assertEqual(json.loads((WIDGET / "language" / "it.json").read_text(encoding="utf-8"))["dictionary"]["title_running"],
                         "Sincronizzazione in corso")


if __name__ == "__main__":
    unittest.main()
