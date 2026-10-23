import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from features.brain.llm import BrainUnavailable
from features.musicstudio import api, catalog, commands, composer, exporter, generator, imports, library, schema, service, store, theory, voicebank
from features.shares import archive


class Sandbox(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for target in (mock.patch.object(store, "DIRECTORY", self.root / "store"), mock.patch.object(archive, "ROOT", self.root / "share")):
            target.start()
            self.addCleanup(target.stop)
        service.jobs.clear()
        commands.state["active"] = ""


class SchemaTest(unittest.TestCase):
    def test_clamps_and_defaults(self):
        project = schema.clean_project({"tempo": 9999, "beats": 99, "genre": "x", "tracks": [{"role": "nope", "volume": 99, "pan": -9, "clips": [{"start": -5, "notes": [{"p": 500, "v": 9, "t": "a"}]}]}]})
        self.assertEqual((project["tempo"], project["beats"], project["genre"]), (220, 7, "pop"))
        track = project["tracks"][0]
        self.assertEqual((track["volume"], track["pan"], track["role"]), (1.5, -1, "lead"))
        self.assertEqual(track["clips"][0]["notes"][0]["p"], 127)

    def test_effects_and_vocal_validation(self):
        track = schema.clean_track({"role": "vocal", "effects": [{"type": "reverb", "params": {"mix": 5}}, {"type": "evil"}],
                                    "clips": [{"vocal": {"text": "<script>ciao</script>", "lang": "zz1", "asset": "../x.wav"}}]})
        self.assertEqual(len(track["effects"]), 1)
        self.assertEqual(track["effects"][0]["params"]["mix"], 1)
        vocal = track["clips"][0]["vocal"]
        self.assertNotIn("<", vocal["text"])
        self.assertEqual((vocal["lang"], vocal["asset"]), ("it", ""))


class GeneratorTest(unittest.TestCase):
    def test_every_genre_arranges(self):
        for genre in catalog.GENRES:
            with self.subTest(genre=genre):
                project = generator.arrange({"genre": genre, "bars": 32, "seed": 5})
                self.assertEqual(project["genre"], genre)
                self.assertGreaterEqual(len(project["tracks"]), 5)
                self.assertEqual(sum(s["bars"] for s in project["structure"]), 32)
                for track in project["tracks"]:
                    self.assertTrue(track["clips"])
                    for clip in track["clips"]:
                        self.assertTrue(all(0 <= n["p"] <= 127 and n["t"] < clip["length"] + 0.01 for n in clip["notes"]))

    def test_theory_triads(self):
        self.assertEqual(theory.triad(0, "major", 0), (0, "maj"))
        self.assertEqual(theory.triad(0, "major", 5), (9, "min"))
        self.assertEqual(theory.triad(0, "minor", 0), (0, "min"))

    def test_add_layer_and_vocal(self):
        project = generator.arrange({"genre": "pop", "seed": 1, "roles": ["drums"]})
        track = generator.add_layer(project, "bass", "bass_sub", seed=2)
        self.assertEqual(track["instrument"], "bass_sub")
        with self.assertRaises(schema.SpecError):
            generator.add_layer(project, "vocal")
        vocal = generator.vocal_track(project, "ciao uno\n\nciao due", "it")
        self.assertEqual(len(vocal["clips"]), 2)


class ComposerTest(unittest.TestCase):
    def test_heuristic(self):
        spec = composer.heuristic("una base trap triste a 140 bpm")
        self.assertEqual((spec["genre"], spec["tempo"], spec["mode"]), ("trap", 140, "minor"))
        self.assertFalse(composer.heuristic("una canzone strumentale pop")["vocals"])

    def test_plan_uses_brain_and_validates(self):
        data = {"title": "Notte", "genre": "lofi", "tempo": 400, "root": 9, "mode": "minor", "bars": 24, "roles": ["drums", "bass", "vocal", "x"],
                "instruments": {"bass": "bass_sub", "lead": "kit_808"}, "vocals": True, "lang": "en", "lyrics": "line one\nline two"}
        with mock.patch.object(composer, "generate", mock.AsyncMock(return_value=data)):
            spec = asyncio.run(composer.plan("canzone lofi"))
        self.assertEqual((spec["genre"], spec["tempo"], spec["root"], spec["roles"], spec["instruments"]), ("lofi", 200, 9, ["drums", "bass"], {"bass": "bass_sub"}))


class StoreTest(Sandbox):
    def test_roundtrip_and_split(self):
        project = generator.arrange({"genre": "house", "seed": 3})
        store.save(project)
        files = sorted(p.name for p in (self.root / "store" / project["id"] / "tracks").iterdir())
        self.assertEqual(len(files), len(project["tracks"]))
        self.assertEqual(store.load(project["id"])["tracks"][0]["id"], project["tracks"][0]["id"])
        project["tracks"].pop()
        store.save(project)
        self.assertEqual(len(list((self.root / "store" / project["id"] / "tracks").iterdir())), len(project["tracks"]))
        store.remove(project["id"])
        self.assertEqual(store.ids(), [])
        with self.assertRaises(KeyError):
            store.load("../etc")


class ServiceTest(Sandbox):
    def test_create_falls_back_without_brain(self):
        async def run():
            project = service.create("una base house")
            await asyncio.sleep(0)
            return project

        with mock.patch.object(composer, "generate", mock.AsyncMock(side_effect=BrainUnavailable("off"))), mock.patch.object(service, "background", lambda coro: asyncio.get_event_loop().create_task(coro)):
            async def main():
                project = await run()
                for _ in range(50):
                    await asyncio.sleep(0.01)
                    if service.status(project["id"])["state"] == "done":
                        break
                return project

            project = asyncio.run(main())
        self.assertEqual(service.status(project["id"])["state"], "done")
        self.assertEqual(store.load(project["id"])["genre"], "house")

    def test_effect_and_tempo(self):
        project = generator.arrange({"genre": "pop", "seed": 1})
        store.save(project)
        updated = service.add_effect(project["id"], "reverb", "bass")
        bass = next(t for t in updated["tracks"] if t["role"] == "bass")
        self.assertIn("reverb", [e["type"] for e in bass["effects"]])
        self.assertEqual(service.set_tempo(project["id"], 500)["tempo"], 220)
        with self.assertRaises(schema.SpecError):
            service.add_effect(project["id"], "evil")


class ApiTest(Sandbox):
    def setUp(self):
        super().setUp()
        app = FastAPI()
        app.dependency_overrides[api.require_admin] = lambda: "admin"
        app.include_router(api.admin_routes)
        self.client = TestClient(app)
        self.project = generator.arrange({"genre": "pop", "seed": 9})
        store.save(self.project)
        self.pid = self.project["id"]

    def test_catalog_and_listing(self):
        body = self.client.get("/api/musicstudio/catalog").json()
        self.assertEqual(len(body["instruments"]), len(catalog.INSTRUMENTS))
        self.assertEqual(len(self.client.get("/api/musicstudio/projects").json()["projects"]), 1)

    def test_layers_put_delete(self):
        added = self.client.post(f"/api/musicstudio/projects/{self.pid}/layers", json={"role": "fx"})
        self.assertEqual(added.status_code, 200)
        self.assertEqual(self.client.post(f"/api/musicstudio/projects/{self.pid}/layers", json={"role": "vocal"}).status_code, 400)
        body = self.client.get(f"/api/musicstudio/projects/{self.pid}").json()
        body["tempo"] = 77
        self.assertEqual(self.client.put(f"/api/musicstudio/projects/{self.pid}", json=body).json()["tempo"], 77)
        self.assertEqual(self.client.delete(f"/api/musicstudio/projects/{self.pid}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/musicstudio/projects/{self.pid}").status_code, 404)

    def test_traversal_and_extra_fields(self):
        self.assertEqual(self.client.get("/api/musicstudio/projects/..%2Fx").status_code, 404)
        self.assertEqual(self.client.get(f"/api/musicstudio/projects/{self.pid}/assets/..%2Fmeta.json").status_code, 404)
        self.assertEqual(self.client.post("/api/musicstudio/projects", json={"prompt": "abc", "evil": 1}).status_code, 422)

    def test_export_requires_wav(self):
        self.assertEqual(self.client.post(f"/api/musicstudio/projects/{self.pid}/export", content=b"nope").status_code, 400)
        ok = self.client.post(f"/api/musicstudio/projects/{self.pid}/export", content=b"RIFF" + b"\x00" * 40)
        self.assertEqual(ok.status_code, 200)
        folder = self.root / "share" / archive.FOLDERS["produzioni"] / ok.json()["folder"]
        self.assertTrue((folder / "progetto.json").is_file())

    def test_translate_without_brain(self):
        with mock.patch.object(service.lyr, "generate", mock.AsyncMock(side_effect=BrainUnavailable("off"))):
            project = store.load(self.pid)
            project["lyrics"] = schema.clean_lyrics({"lang": "it", "text": "ciao"})
            store.save(project)
            self.assertEqual(self.client.post(f"/api/musicstudio/projects/{self.pid}/translate", json={"lang": "en"}).status_code, 503)


class VoiceTest(Sandbox):
    def say(self, text):
        return asyncio.run(commands.answer(text))

    def test_patterns(self):
        self.assertTrue(commands.CREATE.search("crea una canzone lo-fi rilassante"))
        self.assertTrue(commands.CREATE.search("componi un brano rock"))
        self.assertFalse(commands.CREATE.search("metti una canzone di vasco"))

    def test_layer_effect_tempo_and_unknown(self):
        project = generator.arrange({"genre": "pop", "seed": 1, "roles": ["drums"]})
        store.save(project)
        reply, _ = self.say("aggiungi un basso")
        self.assertIn("basso", reply)
        self.assertIn("bass", [t["role"] for t in store.load(project["id"])["tracks"]])
        self.say("aggiungi un riverbero al basso")
        bass = next(t for t in store.load(project["id"])["tracks"] if t["role"] == "bass")
        self.assertIn("reverb", [e["type"] for e in bass["effects"]])
        self.say("rendi la canzone più veloce")
        self.assertGreater(store.load(project["id"])["tempo"], project["tempo"])
        with self.assertRaises(LookupError):
            self.say("che tempo fa domani")

    def test_without_project_is_ignored(self):
        with self.assertRaises(LookupError):
            self.say("aggiungi un basso")


class ExporterTest(Sandbox):
    def test_unsafe_title_is_sanitised(self):
        project = generator.arrange({"genre": "pop", "seed": 1, "title": "../../evil"})
        store.save(project)
        name = exporter.save(project, b"RIFF0000")["folder"]
        self.assertNotIn("..", name)
        self.assertTrue((self.root / "share" / archive.FOLDERS["produzioni"] / name).is_dir())


class BridgeTest(Sandbox):
    def setUp(self):
        super().setUp()
        patch = mock.patch("features.music.layout.archive.ROOT", self.root / "share")
        patch.start()
        self.addCleanup(patch.stop)
        self.project = generator.arrange({"genre": "pop", "seed": 2, "title": "Alba"})
        store.save(self.project)

    def test_library_publish_tags_and_lyrics(self):
        self.project["lyrics"] = schema.clean_lyrics({"lang": "it", "text": "ciao mondo"})
        with mock.patch.object(library, "_rescan") as rescan:
            relative = library.publish(self.project, b"RIFF" + b"\x00" * 40)
        rescan.assert_called_once()
        path = self.root / "share" / archive.FOLDERS["musica"] / relative
        self.assertTrue(path.is_file())
        self.assertIn("Nuxiva Studio", relative)
        self.assertTrue(path.with_suffix(".lrc").is_file())

    def test_browse_and_resolve_block_traversal(self):
        folder = archive.folder("scambio")
        (folder / "a.wav").write_bytes(b"RIFF")
        (folder / "note.txt").write_text("x")
        self.assertEqual([r["path"] for r in imports.browse("scambio")], ["a.wav"])
        with self.assertRaises(schema.SpecError):
            imports.browse("documenti")
        with self.assertRaises(schema.SpecError):
            imports.resolve("scambio", "../../etc/passwd")
        self.assertEqual(imports.resolve("scambio", "a.wav").name, "a.wav")

    def test_bring_adds_audio_track(self):
        folder = archive.folder("scambio")
        (folder / "loop.wav").write_bytes(b"RIFF")

        def fake(source, target):
            target.write_bytes(b"RIFF")
            return 4.0

        with mock.patch.object(imports, "convert", fake):
            updated = asyncio.run(imports.bring(self.project["id"], "scambio", "loop.wav"))
        track = updated["tracks"][-1]
        self.assertEqual(track["role"], "vocal")
        self.assertTrue(track["clips"][0]["vocal"]["asset"])
        self.assertGreater(track["clips"][0]["length"], 3)

    def test_revoice_resynthesizes(self):
        project = store.load(self.project["id"])
        project["lyrics"] = schema.clean_lyrics({"lang": "it", "text": "uno due tre"})
        project["tracks"].append(generator.vocal_track(project, "uno due tre", "it"))
        store.save(project)
        tid = project["tracks"][-1]["id"]
        voices = mock.AsyncMock(return_value=b"RIFF" + b"\x00" * 40)
        with mock.patch("features.voices.synthesis.synthesize", voices):
            updated = asyncio.run(service.revoice(project["id"], tid, "im_nicola", 1.2))
        clip = next(t for t in updated["tracks"] if t["id"] == tid)["clips"][0]["vocal"]
        self.assertEqual((clip["voice"], clip["speed"]), ("im_nicola", 1.2))
        self.assertTrue(clip["asset"])
        with self.assertRaises(KeyError):
            asyncio.run(service.revoice(project["id"], "ffffffff", "x"))

    def test_voicebank_filters_language(self):
        data = {"voices": [{"id": "a", "name": "A", "lang": "it", "gender": "f", "engine": "kokoro", "installed": True},
                           {"id": "b", "name": "B", "lang": "en", "gender": "m", "engine": "kokoro", "installed": True},
                           {"id": "c", "name": "C", "lang": "it", "gender": "m", "engine": "piper", "installed": False},
                           {"id": "d", "name": "D", "lang": "it", "gender": "m", "engine": "studio", "installed": True, "multi": True}]}
        with mock.patch.object(voicebank.overview, "overview", mock.AsyncMock(return_value=data)):
            ids = [v["id"] for v in asyncio.run(voicebank.voices("it"))]
        self.assertEqual(sorted(ids), ["a", "d"])

    def test_api_bridge_endpoints(self):
        app = FastAPI()
        app.dependency_overrides[api.require_admin] = lambda: "admin"
        app.include_router(api.admin_routes)
        client = TestClient(app)
        pid = self.project["id"]
        self.assertEqual(client.get("/api/musicstudio/sources/segreto").status_code, 400)
        self.assertEqual(client.post(f"/api/musicstudio/projects/{pid}/imports", json={"source": "scambio", "path": "../x.wav"}).status_code, 400)
        self.assertEqual(client.post(f"/api/musicstudio/projects/{pid}/tracks/ffffffff/voice", json={"voice": "x"}).status_code, 404)
        with mock.patch.object(library, "_rescan"):
            ok = client.post(f"/api/musicstudio/projects/{pid}/export", content=b"RIFF" + b"\x00" * 40).json()
        self.assertTrue(ok["library"])


if __name__ == "__main__":
    unittest.main()
