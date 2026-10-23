import asyncio
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from features.brain.llm import BrainUnavailable
from features.musicstudio import api, catalog, commands, composer, exporter, expert, generator, agent, broadcast, edits, genres, imports, library, songtext, schema, service, store, theory, voicebank
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
                self.assertGreaterEqual(len(project["tracks"]), 3)
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


class GenreDataTest(unittest.TestCase):
    def test_registry_is_consistent(self):
        self.assertGreaterEqual(len(genres.ALL), 100)
        self.assertEqual(len(genres.IDS), len(set(genres.IDS)))
        for item in genres.ALL:
            with self.subTest(genre=item.id):
                size = item.beats * 4
                for lane, pattern in item.drums.items():
                    self.assertIn(lane, catalog.LANES)
                    self.assertEqual(size % len(pattern), 0)
                self.assertEqual(size % len(item.bass), 0)
                self.assertEqual(size % len(item.comp), 0)
                for ref in (item.kit, item.bass_i, item.chords_i, item.lead_i, item.pad_i, item.arp_i):
                    self.assertIn(ref, catalog.BY_ID)
                self.assertIn(item.mode, catalog.MODES)
                self.assertTrue(not item.prog or item.prog in theory.NAMED)
                self.assertTrue(item.tags and item.feel)

    def test_search_and_families(self):
        self.assertEqual(genres.search("una tarantella veloce")[0].id, "tarantella")
        self.assertEqual(genres.search("canzone napoletana")[0].id, "napoletana")
        self.assertIn("blues", genres.families()["blues"])


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


class BluesTest(unittest.TestCase):
    def test_twelve_bar_shuffle(self):
        project = generator.arrange({"genre": "blues", "seed": 4, "root": 9, "bars": 24})
        self.assertEqual(project["key"]["mode"], "blues")
        self.assertGreater(project["swing"], 0.3)
        self.assertEqual([c["quality"] for c in project["harmony"][:12]], ["dom7"] * 12)
        self.assertEqual([c["root"] for c in project["harmony"][:12]], [9, 9, 9, 9, 2, 2, 9, 9, 4, 2, 9, 4])
        self.assertEqual(next(t for t in project["tracks"] if t["role"] == "lead")["instrument"], "lead_guitar")

    def test_english_version_request(self):
        spec = composer.heuristic("Creami una canzone con sound blues di Napule è in versione inglese")
        self.assertEqual((spec["genre"], spec["lang"], spec["reference"]), ("blues", "en", True))


class EditsTest(unittest.TestCase):
    def setUp(self):
        self.project = generator.arrange({"genre": "blues", "seed": 1})

    def test_apply_valid_and_skip_invalid(self):
        done = edits.apply(self.project, [{"op": "set_track", "track": "bass", "volume": 9, "mute": True}, {"op": "add_effect", "track": "lead", "type": "reverb", "params": {"mix": 0.5}},
                                          {"op": "add_effect", "track": "lead", "type": "evil"}, {"op": "nope"}, "x", {"op": "set_tempo", "tempo": 1000}])
        self.assertEqual([d["op"] for d in done], ["set_track", "add_effect", "set_tempo"])
        bass = edits.find(self.project, "bass")
        self.assertEqual((bass["volume"], bass["mute"]), (1.5, True))
        self.assertEqual(self.project["tempo"], 220)

    def test_master_effect_and_instrument_role_guard(self):
        edits.apply(self.project, [{"op": "add_effect", "track": "master", "type": "compressor"}, {"op": "set_track", "track": "lead", "instrument": "kit_808"}])
        self.assertEqual([e["type"] for e in self.project["master"]["effects"]], ["compressor"])
        self.assertNotEqual(edits.find(self.project, "lead")["instrument"], "kit_808")

    def test_regenerate_and_remove(self):
        count = len(self.project["tracks"])
        edits.apply(self.project, [{"op": "regenerate", "track": "lead", "instrument": "lead_harmonica"}, {"op": "remove_track", "track": "pad"}])
        self.assertEqual(edits.find(self.project, "lead")["instrument"], "lead_harmonica")
        self.assertEqual(len(self.project["tracks"]), count - 1)


class SongTextTest(Sandbox):
    def test_reference_extraction(self):
        self.assertEqual(songtext.reference("crea una canzone blues di Napule è in versione inglese"), "Napule è")
        self.assertEqual(songtext.reference("una base rock di Vasco con la batteria"), "Vasco")
        self.assertEqual(songtext.reference("una canzone triste"), "")

    def test_match_requires_all_words(self):
        rows = {"tracks": [{"id": 1, "title": "Altro", "artist": "X", "album": ""}, {"id": 2, "title": "Napule è", "artist": "Y", "album": "Z"}]}
        with mock.patch.object(songtext.library, "search", return_value=rows):
            self.assertEqual(songtext.match("Napule è")["id"], 2)
            self.assertIsNone(songtext.match("Roma capoccia"))

    def run_enrich(self, found, spec):
        with mock.patch.object(service, "background", lambda coro: coro.close()):
            project = service.create("crea una canzone blues di Brano in versione inglese")
        translated = mock.AsyncMock(return_value="one two\n\nthree four")
        with mock.patch.object(service.composer, "plan", mock.AsyncMock(return_value=spec)), \
                mock.patch.object(service.songtext, "find", mock.AsyncMock(return_value=found)), \
                mock.patch.object(service.lyr, "translate", translated), \
                mock.patch("features.voices.synthesis.synthesize", mock.AsyncMock(return_value=b"RIFF" + b"\x00" * 40)):
            asyncio.run(service._enrich(project["id"], "crea una canzone blues di Brano in versione inglese"))
        return project["id"]

    def test_enrich_translates_library_lyrics(self):
        found = {"id": 5, "title": "Brano", "artist": "Artista", "text": "uno due\n\ntre quattro"}
        pid = self.run_enrich(found, {"genre": "blues", "lang": "en", "vocals": True, "reference": True, "mood": "", "title": "Blues", "bars": 16})
        saved = store.load(pid)
        self.assertEqual(service.status(pid)["notice"], "lyrics_from_library")
        self.assertEqual(saved["lyrics"]["translations"]["en"], "one two\n\nthree four")
        self.assertTrue(any(t["role"] == "vocal" for t in saved["tracks"]))

    def test_enrich_falls_back_to_original_lyrics(self):
        pid = self.run_enrich(None, {"genre": "blues", "lang": "en", "vocals": True, "reference": True, "mood": "", "title": "Blues", "bars": 16, "lyrics": "own words\n\nmore words"})
        self.assertEqual(service.status(pid)["notice"], "original_lyrics")
        self.assertEqual(store.load(pid)["lyrics"]["text"], "own words\n\nmore words")


class ExpertTest(unittest.TestCase):
    def test_restyle_keeps_vocals_when_meter_matches(self):
        project = generator.arrange({"genre": "pop", "seed": 2})
        project["tracks"].append(generator.vocal_track(project, "uno\n\ndue", "it"))
        done = edits.apply(project, [{"op": "restyle", "genre": "house"}])
        self.assertEqual(done, [{"op": "restyle", "target": "house"}])
        self.assertEqual((project["genre"], project["beats"]), ("house", 4))
        self.assertTrue(any(t["role"] == "vocal" for t in project["tracks"]))
        edits.apply(project, [{"op": "restyle", "genre": "waltz"}])
        self.assertEqual(project["beats"], 3)
        self.assertFalse(any(t["role"] == "vocal" for t in project["tracks"]))
        self.assertEqual(edits.apply(project, [{"op": "restyle", "genre": "nope"}]), [])

    def test_brief_and_blend(self):
        self.assertIn("napoletana", expert.brief("serenata napoletana con mandolino"))
        self.assertEqual(expert.blend("blues", "flamenco")["lead"], "lead_oud")
        self.assertEqual(expert.blend("blues", "blues"), {})

    def test_plan_fusion(self):
        data = {"title": "Fusione", "genre": "blues", "second_genre": "flamenco", "tempo": 90, "roles": ["drums", "bass", "lead"]}
        with mock.patch.object(composer, "generate", mock.AsyncMock(return_value=data)):
            spec = asyncio.run(composer.plan("blues flamenco"))
        self.assertEqual(spec["instruments"]["lead"], "lead_oud")


class AgentTest(Sandbox):
    def test_chat_applies_ops(self):
        project = generator.arrange({"genre": "blues", "seed": 3})
        store.save(project)
        reply = {"reply": "Ecco il riverbero.", "ops": [{"op": "add_effect", "track": "lead", "type": "reverb"}, {"op": "set_track", "track": "drums", "volume": 0.4}]}
        with mock.patch.object(agent, "generate", mock.AsyncMock(return_value=reply)):
            result = asyncio.run(agent.chat(project["id"], "più riverbero alla chitarra e batteria piano", []))
        self.assertEqual(len(result["applied"]), 2)
        saved = store.load(project["id"])
        self.assertEqual(edits.find(saved, "drums")["volume"], 0.4)
        self.assertIn("reverb", [e["type"] for e in edits.find(saved, "lead")["effects"]])

    def test_chat_endpoint_without_brain(self):
        project = generator.arrange({"genre": "blues", "seed": 3})
        store.save(project)
        app = FastAPI()
        app.dependency_overrides[api.require_admin] = lambda: "admin"
        app.include_router(api.admin_routes)
        with mock.patch.object(agent, "generate", mock.AsyncMock(side_effect=BrainUnavailable("off"))):
            code = TestClient(app).post(f"/api/musicstudio/projects/{project['id']}/chat", json={"message": "ciao"}).status_code
        self.assertEqual(code, 503)


class BroadcastTest(Sandbox):
    def setUp(self):
        super().setUp()
        self.project = generator.arrange({"genre": "pop", "seed": 6})
        store.save(self.project)
        self.devices = {"cast:a": {"id": "cast:a", "kind": "cast", "name": "Salotto"}, "dlna:b": {"id": "dlna:b", "kind": "dlna", "name": "Cucina"},
                        "dlna:s1": {"id": "dlna:s1", "kind": "sonos", "name": "Sonos 1", "uuid": "RINCON_AAAAAA01400"},
                        "dlna:s2": {"id": "dlna:s2", "kind": "sonos", "name": "Sonos 2", "uuid": "RINCON_BBBBBB01400"}}

    def run_cast(self, requested, everyone=False):
        calls = []

        async def start(device_id, user, ids, index, start, base, repeat="off"):
            calls.append(("start", device_id))
            return {"state": "playing"}

        async def call(device, kind, action, arguments=None):
            calls.append((action, device["id"], (arguments or {}).get("CurrentURI")))
            return {}

        fake = types.SimpleNamespace(devices=self.devices, start=start, device=lambda d: self.devices[d])

        store.set_published(self.project["id"], "x.wav")
        with mock.patch.object(broadcast, "outputs", fake), mock.patch.object(broadcast.dlna, "call", call), mock.patch.object(broadcast.library, "ensure_indexed", return_value=7):
            rows = asyncio.run(broadcast.cast(self.project["id"], requested, everyone, "admin", "http://x"))
        return rows, calls

    def test_sonos_are_grouped_natively(self):
        rows, calls = self.run_cast(["dlna:s1", "dlna:s2"])
        self.assertEqual([r["role"] for r in rows], ["leader", "follower"])
        self.assertIn(("SetAVTransportURI", "dlna:s2", "x-rincon:RINCON_AAAAAA01400"), calls)

    def test_everyone_mixes_kinds(self):
        rows, calls = self.run_cast([], True)
        self.assertEqual(sorted(r["device"] for r in rows if r["role"] == "sync"), ["cast:a", "dlna:b"])
        self.assertEqual(len(rows), 4)

    def test_requires_render_and_devices(self):
        with mock.patch.object(broadcast.library, "ensure_indexed", return_value=None):
            with self.assertRaises(LookupError):
                asyncio.run(broadcast.cast(self.project["id"], ["cast:a"], False, "admin", "http://x"))
        with self.assertRaises(ValueError):
            with mock.patch.object(broadcast, "outputs", mock.Mock(devices={})), mock.patch.object(broadcast.library, "ensure_indexed", return_value=3):
                asyncio.run(broadcast.cast(self.project["id"], [], False, "admin", "http://x"))

    def test_latency_learning(self):
        device = {"id": "cast:a", "kind": "cast"}
        broadcast.latency.clear()
        broadcast.learn(device, 2.0)
        broadcast.learn(device, 1.0)
        self.assertAlmostEqual(broadcast.estimate(device), 1.6, places=2)


if __name__ == "__main__":
    unittest.main()
