import asyncio
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from access import require_admin
from agenti.firewall import api as firewall_api

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "backend"), str(ROOT / "agenti" / "percezione" / "ear")):
    if p not in sys.path:
        sys.path.insert(0, p)

from agenti.ear import defense_view
from agenti.firewall.defense import stage as stage_module
from agenti.firewall.defense.guardian import guardian
from tests.test_firewall_runtime import FirewallBase

WEB = ROOT / "web" / "display"
DEFENSE = WEB / "defense"
INCIDENT = {"id": "i1", "kinds": ["port_scan"], "stage": "recon", "level": "high", "country": "RU", "origin": "internet",
            "src": "8.8.4.4", "targets": ["192.168.1.5", "192.168.1.6"], "last_at": 10.0}


class SanitiserTests(unittest.TestCase):
    def test_unknown_values_fall_back_to_safe_defaults(self):
        scene = defense_view.clean_scene({"posture": "<script>", "mode": 5, "autonomy": None, "lan": -4, "trusted": "x", "incidents": "no"})
        self.assertEqual(scene["posture"], "calm")
        self.assertEqual(scene["lan"], 0)
        self.assertEqual(scene["incidents"], [])

    def test_text_is_stripped_and_bounded(self):
        row = defense_view.clean_scene({"incidents": [{**INCIDENT, "src": "x" * 500 + "\n\x00", "country": "ru", "hosts": ["h"] * 50,
                                                       "level": "nuclear", "stage": "boom"}]})["incidents"][0]
        self.assertEqual(len(row["src"]), defense_view.TEXT)
        self.assertEqual(row["country"], "")
        self.assertEqual(row["level"], "low")
        self.assertEqual(row["stage"], "recon")
        self.assertEqual(len(row["hosts"]), 6)

    def test_rows_and_numbers_are_capped(self):
        scene = defense_view.clean_scene({"incidents": [INCIDENT] * 100, "defenses": [{"kind": "block", "target": "a", "expires": float("nan")}] * 100,
                                          "lan": float("inf")})
        self.assertEqual(len(scene["incidents"]), defense_view.MAX_ROWS)
        self.assertEqual(len(scene["defenses"]), defense_view.MAX_ROWS)
        self.assertEqual(scene["defenses"][0]["expires"], 0)
        self.assertEqual(scene["lan"], 0)

    def test_control_broadcasts_only_clean_events(self):
        seen = []

        async def broadcast(**event):
            seen.append(event)

        asyncio.run(defense_view.defense_control("defense_view", {"open": True, "scene": {"posture": "attack", "x": 1}}, broadcast))
        asyncio.run(defense_view.defense_control("defense_view", {"open": "yes"}, broadcast))
        asyncio.run(defense_view.defense_control("defense_state", {"auto": 1, "scene": {"posture": "alert"}}, broadcast))
        self.assertEqual(seen[0]["scene"]["posture"], "attack")
        self.assertNotIn("x", seen[0]["scene"])
        self.assertEqual(seen[1], {"type": "defense_view", "open": False})
        self.assertNotIn("auto", seen[2])

    def test_browsers_cannot_send_defense_controls(self):
        from agenti.ear import proxy
        self.assertFalse(defense_view.CONTROLS & proxy.REMOTE_CONTROLS)


class StageTests(FirewallBase):
    def setUp(self):
        super().setUp()
        self.old = guardian.assessment
        guardian.assessment = {**guardian.assessment, "posture": "attack", "incidents": [INCIDENT]}

    def tearDown(self):
        guardian.assessment = self.old
        super().tearDown()

    def test_scene_carries_hosts_of_each_incident(self):
        scene = stage_module.scene()
        self.assertEqual(scene["incidents"][0]["hosts"], ["192.168.1.5", "192.168.1.6"])

    def test_state_is_pushed_only_while_the_view_was_requested(self):
        stage = stage_module.Stage()
        sent = []

        async def send(message):
            sent.append(message)
            return True

        stage.send = send
        asyncio.run(stage.update("attack"))
        self.assertEqual(sent, [])
        asyncio.run(stage.show())
        asyncio.run(stage.update("attack"))
        self.assertEqual([m["type"] for m in sent], ["defense_view", "defense_state"])
        asyncio.run(stage.close())
        asyncio.run(stage.update("attack"))
        self.assertEqual(len(sent), 3)

    def test_show_opens_and_keeps_watching(self):
        stage = stage_module.Stage()
        sent = []

        async def send(message):
            sent.append(message)
            return True

        stage.send = send
        self.assertTrue(asyncio.run(stage.show()))
        self.assertTrue(sent[0]["open"])
        self.assertGreater(stage.watch_until, 0)
        asyncio.run(stage.update("calm"))
        self.assertEqual(sent[-1]["type"], "defense_state")
        asyncio.run(stage.close())
        self.assertEqual(stage.watch_until, 0.0)

    def test_unreachable_screen_is_reported(self):
        stage = stage_module.Stage()
        with mock.patch.object(stage_module.websockets, "connect", side_effect=OSError("down")):
            self.assertFalse(asyncio.run(stage.show()))


class RouteTests(FirewallBase):
    def setUp(self):
        super().setUp()
        app = FastAPI()
        app.include_router(firewall_api.admin_routes)
        app.dependency_overrides[require_admin] = lambda: "nunzio"
        self.client = TestClient(app)

    def test_view_route_opens_and_closes(self):
        with mock.patch.object(stage_module.stage, "send", new=mock.AsyncMock(return_value=True)) as send:
            opened = self.client.post("/api/firewall/defense/view", json={"open": True}).json()
            closed = self.client.post("/api/firewall/defense/view", json={"open": "x"}).json()
        self.assertEqual(opened, {"open": True, "reached": True})
        self.assertEqual(closed, {"open": False, "reached": True})
        self.assertEqual([c.args[0]["open"] for c in send.call_args_list], [True, False])

    def test_view_route_needs_admin(self):
        app = FastAPI()
        app.include_router(firewall_api.admin_routes)
        self.assertIn(TestClient(app).post("/api/firewall/defense/view", json={"open": True}).status_code, (401, 403))


class AssetTests(unittest.TestCase):
    def test_bundles_are_accepted_by_the_real_resolver(self):
        from agenti.locale.colocated.domain import Locale, Scope
        from agenti.locale.colocated.repository import LanguageFileRepository
        from agenti.locale.colocated.resolver import BundleResolver
        from agenti.locale.colocated.roots import ScopeRoots
        from config import UI_LANGUAGES, WEB_DIR
        resolver = BundleResolver(ScopeRoots({"web": (WEB_DIR,)}), LanguageFileRepository(), ("en", "it"))
        for code in ("it", "en", "fr", "es"):
            bundle = resolver.resolve(Scope.parse("web/display/defense"), Locale.parse(code, frozenset(UI_LANGUAGES)))
            self.assertIn("p_attack", bundle.dictionary)
            self.assertEqual(len(bundle.fallback_keys), 0)

    def test_languages_have_same_keys(self):
        bundles = {c: json.loads((DEFENSE / "language" / f"{c}.json").read_text("utf-8")) for c in ("it", "en", "fr", "es")}
        keys = set(bundles["it"]["dictionary"])
        for code, bundle in bundles.items():
            self.assertEqual(set(bundle["dictionary"]), keys, code)
            self.assertEqual(bundle["meta"]["scope"], "web/display/defense")

    def test_page_is_wired(self):
        html = (WEB / "display.html").read_text("utf-8")
        self.assertIn("/static/display/defense/defense.css", html)
        self.assertIn("/static/display/defense/view.js", html)
        self.assertIn("defense_view", (WEB / "ear.js").read_text("utf-8"))

    def test_scripts_stay_small_and_use_text_nodes(self):
        for name in ("view.js", "scene.js", "countries.js"):
            source = (DEFENSE / name).read_text("utf-8")
            self.assertLess(len(source.splitlines()), 500)
            self.assertNotIn("innerHTML", source)
            self.assertNotIn("eval(", source)


if __name__ == "__main__":
    unittest.main()
