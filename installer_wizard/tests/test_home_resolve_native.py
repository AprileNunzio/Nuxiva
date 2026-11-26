import asyncio
import unittest
from unittest import mock

import native_core

from agenti.home_assistant.nlu import resolver
from agenti.home_assistant.nlu.matching import Catalog, area_names
from agenti.home_assistant.nlu.parser import parse, understand
from agenti.home_assistant.nlu.text import phrase_stems

READY = native_core.symbol("RustHomeResolver") is not None
AREAS = (("camera", "Camera da letto"), ("cucina", "Cucina"), ("soggiorno", "Soggiorno"), ("ospiti", "Camera ospiti"))
ENTITIES = (
    ("light.plafoniera", "Plafoniera", "camera", {"brightness"}),
    ("light.comodino", "Abat-jour comodino", "camera", {"brightness"}),
    ("light.cucina", "Luce cucina", "cucina", {"brightness"}),
    ("light.lampadario", "Lampadario", "soggiorno", {"brightness", "color"}),
    ("cover.soggiorno", "Tapparella soggiorno", "soggiorno", {"position"}),
    ("switch.caffe", "Macchina del caffè", "cucina", set()),
    ("light.ospiti", "Luce ospiti", "ospiti", set()),
)
BEDROOM = ["light.comodino", "light.plafoniera"]


def catalog() -> Catalog:
    cat = Catalog()
    names = [n for _, n in AREAS]
    for aid, name in AREAS:
        cat.areas[aid] = {"name": name, "floor_id": None, "labels": [name], "names": area_names(name, [], names)}
    for eid, name, aid, caps in ENTITIES:
        cat.entities[eid] = {"entity_id": eid, "domain": eid.split(".")[0], "name": name, "area_id": aid, "device_id": eid,
                             "controllable": True, "names": [phrase_stems(name)], "labels": [name], "caps": caps,
                             "state": "off", "attrs": {}, "is_group": False, "as_light": False}
    return cat


def targets(plan: dict) -> list[str]:
    return sorted(x for c in plan["calls"] for x in c["entity_ids"])


@unittest.skipUnless(READY, "modulo nativo non disponibile")
class UnderstandTests(unittest.TestCase):

    def setUp(self):
        self.cat = catalog()

    def test_bedroom_lights_in_any_wording(self):
        for text in ("accendi le luci della camera da letto", "accendi la luce della camera da letto",
                     "camera da letto accendi le luci", "luci camera da letto accese", "turn on the bedroom lights",
                     "enciende las luces del dormitorio", "allume les lumières de la chambre", "accendi la camera da letto"):
            plan = understand(text, self.cat)
            self.assertEqual(plan["kind"], "command", text)
            self.assertEqual(targets(plan), BEDROOM, text)
            self.assertEqual(plan["calls"][0]["service"], "turn_on", text)
            self.assertFalse(plan["confirm"], text)

    def test_room_named_only_by_its_first_word(self):
        plan = understand("accendi le luci in camera", self.cat)
        self.assertEqual(plan["kind"], "ask")
        self.assertIn("Camera da letto", plan["speech"])
        self.assertIn("Camera ospiti", plan["speech"])
        cover = understand("chiudi la tapparella del soggiorno", self.cat)
        self.assertEqual(cover["calls"][0]["service"], "close_cover")

    def test_names_and_parameters(self):
        plan = understand("accendi il lampadario al 40%", self.cat)
        self.assertEqual(targets(plan), ["light.lampadario"])
        self.assertEqual(plan["calls"][0]["data"], {"brightness_pct": 40})
        self.assertEqual(targets(understand("spegni la macchina del caffè", self.cat)), ["switch.caffe"])

    def test_ambiguity_becomes_a_question_never_a_lesson(self):
        plan = understand("accendi la luce", self.cat)
        self.assertEqual(plan["kind"], "ask")
        self.assertNotIn("devi dire", plan["speech"].lower())
        self.assertIn("Cucina", plan["speech"])

    def test_medium_confidence_asks_a_short_confirmation(self):
        plan = understand("acendi le lucci della camera da leto", self.cat)
        self.assertEqual(targets(plan), BEDROOM)
        if plan["confirm"]:
            self.assertTrue(plan["question"].startswith("Intende accendere"))

    def test_queries_stay_on_the_rules(self):
        self.assertEqual(understand("le luci della cucina sono accese?", self.cat), parse("le luci della cucina sono accese?", self.cat))

    def test_unknown_requests_are_left_to_others(self):
        self.assertIsNone(resolver.plan("che tempo fa domani", self.cat, {}))


class FallbackTests(unittest.TestCase):

    def test_without_native_the_rules_answer(self):
        cat = catalog()
        with mock.patch.object(native_core, "symbol", return_value=None):
            self.assertIsNone(resolver.plan("accendi le luci della camera da letto", cat, {}))
            self.assertEqual(understand("accendi la luce della cucina", cat), parse("accendi la luce della cucina", cat))

    def test_inventory_is_bounded_and_clean(self):
        cat = catalog()
        cat.entities["light.lunga"] = dict(cat.entities["light.cucina"], entity_id="light.lunga", name="x" * 900)
        cat.entities["bad"] = dict(cat.entities["light.cucina"], entity_id="switch.altro")
        inv = resolver.inventory(cat)
        self.assertTrue(all(len(e["name"].encode()) <= resolver.MAX_NAME_BYTES for e in inv["entities"]))
        self.assertNotIn("switch.altro", [e["id"] for e in inv["entities"]])


@unittest.skipUnless(READY, "modulo nativo non disponibile")
class ClaimTests(unittest.TestCase):

    def test_room_called_camera_is_not_the_webcam(self):
        from agenti.home_assistant.home import brain
        from agenti.understanding import claims, context
        with mock.patch.object(brain, "catalog", catalog()):
            room = context.build("accendi le luci della camera da letto", None)
            self.assertGreater(claims.home(room), claims.livecam(room))
            cam = context.build("accendi la webcam", None)
            self.assertEqual(claims.livecam(cam), 0.95)


@unittest.skipUnless(READY, "modulo nativo non disponibile")
class ConfirmFlowTests(unittest.TestCase):

    def test_confirmation_runs_the_pending_plan(self):
        from agenti.home_assistant.home import brain
        plan = understand("accendi le luci della camera da letto", catalog())
        plan["confirm"] = True
        ran = {}

        async def run(p, text, source, started=None):
            ran["plan"] = p
            return "Fatto.", {"mode": "face"}, "casa"

        settings = {"enabled": True, "url": "http://ha.local", "token": "t", "confirm": True}
        with mock.patch.object(brain, "entities", {"light.plafoniera": {}}), \
                mock.patch.object(brain, "settings", return_value=settings), \
                mock.patch.object(brain, "status", "online"), \
                mock.patch("agenti.home_assistant.commands.understand", return_value=plan), \
                mock.patch.object(brain, "_refusal", return_value=""), \
                mock.patch.object(brain, "_run", side_effect=run):
            speech, _, agent = asyncio.run(brain.handle("accendi le luci della camera da letto"))
            self.assertIn("Intende accendere", speech)
            self.assertEqual(agent, "casa · conferma")
            asyncio.run(brain.handle("sì"))
        self.assertEqual(ran["plan"]["entities"], plan["entities"])


if __name__ == "__main__":
    unittest.main()
