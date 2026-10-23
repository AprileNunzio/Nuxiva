import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from features.brain.llm import BrainUnavailable
from features.diorama import api, catalog, planner, service, spec, store, templates


class Sandbox(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        patch = mock.patch.object(store, "DIRECTORY", Path(tmp.name))
        patch.start()
        self.addCleanup(patch.stop)
        service.jobs.clear()


class SpecTest(unittest.TestCase):
    def test_item_is_clamped_and_defaulted(self):
        item = spec.clean_item({"kind": "tree_cherry", "x": 9999, "z": "x", "scale": 99, "params": {"height": -4, "color": "red"}})
        self.assertEqual(item["x"], spec.COORD)
        self.assertEqual(item["z"], 0.0)
        self.assertEqual(item["scale"], 5.0)
        self.assertEqual(item["params"]["height"], 0.8)
        self.assertEqual(item["params"]["color"], catalog.BY_ID["tree_cherry"].params["color"].default)

    def test_unknown_kind_and_text_sanitised(self):
        with self.assertRaises(spec.SpecError):
            spec.clean_item({"kind": "nuke"})
        item = spec.clean_item({"kind": "sign", "params": {"text": "<script>HELLO</script>"}})
        self.assertNotIn("<", item["params"]["text"])

    def test_items_capped(self):
        rows = [{"kind": "rock"}] * (spec.MAX_ITEMS + 50)
        self.assertEqual(len(spec.clean_items(rows)), spec.MAX_ITEMS)

    def test_look_defaults(self):
        look = spec.clean_look({"light": "lava", "lens": "fisheye", "blur": 9})
        self.assertEqual((look["light"], look["lens"], look["blur"]), (catalog.LIGHT_DEFAULT, catalog.LENS_DEFAULT, 1.0))


class TemplateTest(unittest.TestCase):
    def test_japan_template_is_complete(self):
        plan = templates.compose("stazione giapponese con ciliegi", seed=1)
        self.assertEqual(set(plan["stages"]), set(templates.STAGES))
        kinds = {i["kind"] for rows in plan["stages"].values() for i in rows}
        self.assertTrue({"rails", "platform", "train", "tree_cherry", "station_building"} <= kinds)

    def test_generic_template(self):
        self.assertIn("pond", {i["kind"] for rows in templates.compose("un giardino")["stages"].values() for i in rows})


class ServiceTest(Sandbox):
    def run_build(self, prompt):
        async def go():
            with mock.patch.object(service, "PACE", 0), mock.patch.object(planner, "generate", side_effect=BrainUnavailable("x")):
                record = service.create(prompt)
                await asyncio.sleep(0)
                await service._build(record["id"])
                return record["id"]
        with mock.patch.object(service, "background", lambda coro: coro.close()):
            return asyncio.run(go())

    def test_fallback_build_populates_everything(self):
        did = self.run_build("stazione giapponese")
        record = store.load(did)
        self.assertGreater(len(record["items"]), 30)
        self.assertEqual(service.status(did)["state"], "done")
        self.assertEqual(service.status(did)["mode"], "template")

    def test_ops_add_update_remove(self):
        record = {"items": [spec.clean_item({"kind": "rock", "x": 1})], "look": spec.clean_look({})}
        rid = record["items"][0]["id"]
        changed = service._apply_ops(record, {"ops": [
            {"op": "add", "item": {"kind": "bench", "x": 2}},
            {"op": "update", "id": rid, "item": {"x": 5, "kind": "car"}},
            {"op": "remove", "id": "deadbeef"},
            {"op": "add", "item": {"kind": "nope"}},
        ], "look": {"light": "blue_hour"}})
        self.assertEqual(changed, 3)
        self.assertEqual(record["look"]["light"], "blue_hour")
        updated = next(i for i in record["items"] if i["id"] == rid)
        self.assertEqual((updated["x"], updated["kind"]), (5.0, "rock"))

    def test_short_prompt_rejected(self):
        with self.assertRaises(spec.SpecError):
            service.create("a")


class ApiTest(Sandbox):
    def setUp(self):
        super().setUp()
        app = FastAPI()
        app.dependency_overrides[api.require_admin] = lambda: "admin"
        app.include_router(api.admin_routes)
        self.client = TestClient(app)
        record = {"id": "0a1b2c3d", "title": "t", "story": "", "prompt": "p", "created": 1, "base": spec.clean_base({}),
                  "look": spec.clean_look({}), "items": [], "revision": 0}
        store.save(record)

    def test_catalog(self):
        body = self.client.get("/api/diorama/catalog").json()
        self.assertEqual(len(body["kinds"]), len(catalog.KINDS))

    def test_item_lifecycle(self):
        added = self.client.post("/api/diorama/0a1b2c3d/items", json={"kind": "bench", "x": 3}).json()
        iid = added["id"]
        moved = self.client.put(f"/api/diorama/0a1b2c3d/items/{iid}", json={"x": 4, "kind": "car"}).json()
        self.assertEqual((moved["x"], moved["kind"]), (4.0, "bench"))
        self.assertEqual(self.client.delete(f"/api/diorama/0a1b2c3d/items/{iid}").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/diorama/0a1b2c3d/items/{iid}").status_code, 404)

    def test_look_and_unknown(self):
        look = self.client.put("/api/diorama/0a1b2c3d/look", json={"light": "overcast", "lens": "macro"}).json()
        self.assertEqual((look["light"], look["lens"]), ("overcast", "macro"))
        self.assertEqual(self.client.get("/api/diorama/ffffffff").status_code, 404)
        self.assertEqual(self.client.get("/api/diorama/..%2Fx").status_code, 404)

    def test_extra_fields_rejected(self):
        self.assertEqual(self.client.put("/api/diorama/0a1b2c3d/look", json={"evil": 1}).status_code, 422)


if __name__ == "__main__":
    unittest.main()


class VoiceTest(Sandbox):
    def setUp(self):
        super().setUp()
        from features.diorama import commands
        self.commands = commands
        record = {"id": "0a1b2c3d", "title": "Stazione", "story": "", "prompt": "p", "created": 1, "base": spec.clean_base({}),
                  "look": spec.clean_look({}), "items": [], "revision": 0}
        store.save(record)
        self.shown = []
        self.desk = mock.MagicMock()
        self.desk.instances = {}
        self.desk.show.side_effect = lambda wid, data, **kw: self.shown.append((wid, data, kw))
        patch = mock.patch.object(commands, "desk", self.desk)
        patch.start()
        self.addCleanup(patch.stop)

    def say(self, text):
        return asyncio.run(self.commands.answer(text))

    def activate(self):
        self.desk.instances = {"diorama:0a1b2c3d": {"id": "diorama", "data": {"id": "0a1b2c3d"}}}

    def test_create_opens_fullscreen(self):
        with mock.patch.object(service, "background", lambda coro: coro.close()):
            reply, _ = self.say("creami un diorama di una stazione giapponese con i ciliegi")
        self.assertIn("costruirlo", reply)
        self.assertEqual(self.shown[-1][0], "diorama")
        self.desk.fullscreen.assert_called_once()

    def test_unrelated_text_is_not_handled(self):
        with self.assertRaises(LookupError):
            self.say("accendi la luce del salotto")
        self.activate()
        with self.assertRaises(LookupError):
            self.say("accendi la luce del salotto")

    def test_light_and_lens_by_voice(self):
        self.activate()
        self.assertEqual(self.say("fai tramonto")[0], "Ora d'oro.")
        self.say("metti la notte")
        self.say("passa al macro")
        look = store.load("0a1b2c3d")["look"]
        self.assertEqual((look["light"], look["lens"]), ("night", "macro"))

    def test_blur_and_angle(self):
        self.activate()
        self.say("più sfocato")
        self.say("vista dall'alto")
        look = store.load("0a1b2c3d")["look"]
        self.assertAlmostEqual(look["blur"], 0.8)
        self.assertGreater(look["angle"], 38)

    def test_edit_goes_to_agent(self):
        self.activate()
        called = []
        with mock.patch.object(self.commands, "background", lambda coro: (called.append(1), coro.close())):
            reply, _ = self.say("aggiungi un ciliegio a sinistra")
        self.assertEqual(called, [1])
        self.assertIn("modifico", reply)

    def test_list_and_close(self):
        self.assertIn("Stazione", self.say("quali diorami hai")[0])
        self.activate()
        self.say("chiudi il diorama")
        self.desk.dismiss.assert_called_once_with("diorama:0a1b2c3d")


class MotionTest(unittest.TestCase):
    def test_motion_only_for_movers_and_clamped(self):
        train = spec.clean_item({"kind": "train", "motion": {"axis": "z", "speed": 99, "span": 1}})
        self.assertEqual(train["motion"], {"axis": "z", "speed": 4.0, "span": 4.0})
        self.assertEqual(spec.clean_item({"kind": "bench", "motion": {"speed": 2}})["motion"], {})
        self.assertEqual(spec.clean_item({"kind": "car", "motion": {"speed": 0}})["motion"], {})

    def test_template_train_moves(self):
        plan = templates.compose("stazione giapponese", seed=2)
        train = next(i for i in plan["stages"]["life"] if i["kind"] == "train")
        self.assertGreater(train["motion"]["speed"], 0)


class AmbientTest(Sandbox):
    def setUp(self):
        super().setUp()
        from features.diorama import ambient
        self.ambient = ambient
        ambient.state.update({"last": 0.0, "busy": False})
        self.shown = []
        patch = mock.patch.object(ambient, "present", lambda did, **kw: self.shown.append((did, kw)))
        patch.start()
        self.addCleanup(patch.stop)

    def test_gate(self):
        a = self.ambient
        with mock.patch.object(a, "enabled", return_value=True):
            self.assertTrue(a.worthwhile("raccontami la storia dei treni a vapore", "I treni a vapore nacquero nell'Ottocento", 1000.0))
            self.assertFalse(a.worthwhile("ciao", "ciao a te, come stai oggi?", 1000.0))
            self.assertFalse(a.worthwhile("accendi la luce in cucina per favore", "fatto, luce accesa in cucina", 1000.0))
            a.state["last"] = 950.0
            self.assertFalse(a.worthwhile("raccontami la storia dei treni a vapore", "I treni a vapore nacquero nell'Ottocento", 1000.0))
        with mock.patch.object(a, "enabled", return_value=False):
            a.state["last"] = 0.0
            self.assertFalse(a.worthwhile("raccontami la storia dei treni a vapore", "I treni a vapore nacquero nell'Ottocento", 1000.0))

    def run_decide(self, answer):
        async def go():
            with mock.patch.object(self.ambient, "generate", mock.AsyncMock(return_value=answer)), mock.patch.object(service, "background", lambda c: c.close()):
                await self.ambient.decide("parliamo dei treni a vapore", "Erano macchine affascinanti e potenti")
        asyncio.run(go())

    def test_decide_shows_small_scene(self):
        self.run_decide({"show": True, "scene": "un treno a vapore che passa in una stazione di campagna", "mood": "golden_hour"})
        self.assertEqual(len(self.shown), 1)
        self.assertEqual(self.shown[0][1], {"immersive": False, "ttl": self.ambient.SHOW_SECONDS})
        self.assertTrue(store.load(self.shown[0][0])["ambient"])
        self.assertFalse(self.ambient.state["busy"])

    def test_decide_declines(self):
        self.run_decide({"show": False, "scene": ""})
        self.run_decide({"show": True, "scene": "x"})
        self.assertEqual(self.shown, [])


class LearningTest(Sandbox):
    def setUp(self):
        super().setUp()
        from features.diorama import learned, learning
        self.learned, self.learning = learned, learning
        patch = mock.patch.object(learned, "FILE", store.DIRECTORY / "learned.json")
        patch.start()
        self.addCleanup(patch.stop)
        learning.state.update({"last_turn": 0.0, "last_run": 0.0, "running": False})

    def recipe(self, count=6):
        return {"parts": [{"shape": "box", "x": i * 0.2, "w": 0.3, "h": 0.4, "d": 0.3, "color": "#aa5533", "tint": i == 0} for i in range(count)], "mover": False}

    def test_recipe_validation_and_dedupe(self):
        self.assertIsNone(self.learned.clean_recipe({"parts": [{"shape": "box"}]}))
        self.assertIsNone(self.learned.clean_recipe({"parts": [{"shape": "laser"}] * 5}))
        kind = self.learned.add("Fontana", "una fontana", self.recipe(), 1)
        self.assertEqual(kind, "x_fontana")
        self.assertIsNone(self.learned.add("Fontana", "dup", self.recipe(), 2))
        self.assertIsNone(self.learned.add("Treno", "x", {"parts": []}, 3))

    def test_part_limits(self):
        row = self.learned.clean_recipe({"parts": [{"shape": "box", "w": 9999, "x": -9999, "color": "red", "material": "lava"}] * 60})
        self.assertEqual(len(row["parts"]), self.learned.MAX_PARTS)
        self.assertEqual((row["parts"][0]["w"], row["parts"][0]["x"], row["parts"][0]["material"], row["parts"][0]["color"]), (12.0, -8.0, "paint", "#b0b0b0"))

    def test_learned_kind_usable_in_scene_and_catalog(self):
        self.learned.add("Fontana", "una fontana", self.recipe(), 1)
        item = spec.clean_item({"kind": "x_fontana", "x": 2, "params": {"color": "#112233", "evil": 1}})
        self.assertEqual(item["params"], {"color": "#112233"})
        self.assertIn("x_fontana", [k["id"] for k in catalog.public()["kinds"]])
        self.assertIn("x_fontana", catalog.prompt_catalog())
        with self.assertRaises(spec.SpecError):
            spec.clean_item({"kind": "x_missing"})

    def test_remove(self):
        self.learned.add("Fontana", "", self.recipe(), 1)
        self.assertTrue(self.learned.remove("x_fontana"))
        self.assertFalse(self.learned.remove("x_fontana"))

    def test_gate(self):
        self.assertFalse(self.learning.due(100.0))
        with mock.patch.object(self.learning, "enabled", return_value=True):
            self.assertTrue(self.learning.due(self.learning.INTERVAL_SECONDS + 700))
            self.learning.state["last_turn"] = self.learning.INTERVAL_SECONDS + 600
            self.assertFalse(self.learning.due(self.learning.INTERVAL_SECONDS + 700))

    def test_study_designs_and_filters_private(self):
        rows = [("parliamo dei vecchi trattori a cingoli nel campo", "r"), ("il mio conto in banca è in rosso", "r"), ("accendi la luce del salotto", "r")]
        picks = {"subjects": [{"label": "Trattore", "hint": "un trattore agricolo"}, {"label": "Diagnosi", "hint": "una malattia"}]}
        calls = []

        async def fake(prompt, **kw):
            calls.append(prompt)
            return picks if "curate" in kw["system"] else self.recipe()

        with mock.patch.object(self.learning.history, "recent_all", return_value=rows), mock.patch.object(self.learning, "generate", fake):
            made = asyncio.run(self.learning.study_once())
        self.assertEqual(made, ["x_trattore"])
        self.assertNotIn("conto", calls[0])
        self.assertNotIn("luce del salotto", calls[0])
        self.assertFalse(self.learning.state["running"])

    def test_api_learned(self):
        self.learned.add("Fontana", "una fontana", self.recipe(), 1)
        app = FastAPI()
        app.dependency_overrides[api.require_admin] = lambda: "admin"
        app.include_router(api.admin_routes)
        client = TestClient(app)
        body = client.get("/api/diorama/learned").json()
        self.assertEqual(body["items"][0]["id"], "x_fontana")
        self.assertEqual(client.delete("/api/diorama/learned/x_fontana").status_code, 200)
        self.assertEqual(client.delete("/api/diorama/learned/x_fontana").status_code, 404)
        self.assertEqual(client.delete("/api/diorama/learned/X_bad").status_code, 404)


class RecallTests(unittest.TestCase):
    def test_similar_prompts_match_and_unrelated_do_not(self):
        from features.diorama import recall
        a = recall.tokens("stazione giapponese sotto la neve con treno")
        self.assertGreaterEqual(recall.score(a, recall.tokens("una stazione giapponese con il treno sotto la neve")), recall.THRESHOLD)
        self.assertLess(recall.score(a, recall.tokens("giardino zen con laghetto")), recall.THRESHOLD)


class VisualShowTests(unittest.TestCase):
    def test_pattern(self):
        from features.diorama import commands
        for ok in ("mostrami un treno", "fammi vedere una locomotiva", "mostrami il Colosseo", "fammi vedere un castello medievale"):
            with self.subTest(ok=ok):
                self.assertTrue(commands.VISUAL.match(ok))
                self.assertFalse(commands.NOT_VISUAL.search(ok))
        for no in ("mostrami il modello 3d di un martello", "mostrami la telecamera del garage", "mostrami il meteo", "mostrami le foto"):
            with self.subTest(no=no):
                m = commands.VISUAL.match(no)
                self.assertTrue(not m or commands.NOT_VISUAL.search(no) or commands.FOREIGN.search(no))


class ExportTests(unittest.TestCase):
    def test_saved_to_share(self):
        from features.diorama import export
        from features.shares import archive
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(archive, "ROOT", Path(tmp)), mock.patch.object(store, "DIRECTORY", Path(tmp) / "st"):
            record = {"id": "a1b2c3d4", "title": "Treno", "story": "", "prompt": "un treno", "created": 1, "base": spec.clean_base({}),
                      "look": spec.clean_look({}), "items": [spec.clean_item({"kind": "house", "x": 0, "z": 0})], "revision": 1, "ambient": False}
            store.save(record)
            export.save(record["id"])
            files = list((Path(tmp) / archive.FOLDERS["diorami"]).glob("*.json"))
            self.assertEqual(len(files), 1)
