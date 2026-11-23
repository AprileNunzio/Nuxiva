import asyncio
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from access import require_admin
from agenti.ai_studio import api
from agenti.ai_studio.inference_service import StudioBrainUnavailable, build_prompt
from agenti.ai_studio.memory_service import CrossMemoryService
from agenti.ai_studio.service import StudioService
from agenti.ai_studio.smb_service import SmbStudioService
from agenti.ai_studio.store import StudioStore
from agenti.ai_studio.voice_log import api as voice_api
from agenti.ai_studio.voice_log.service import VoiceLogService
from agenti.chat.interactions import trail
from agenti.chat.interactions.store import Interaction, InteractionStore


class FakeJournal:
    def __init__(self) -> None:
        self.entries = {}
        self.clips = {}
        self.verdicts = {}

    def add(self, ref: str, ts: float, text: str, audio: bytes | None = None) -> None:
        self.entries[ref] = {"id": ref, "ts": ts, "text": text, "lang": "it", "speaker": "nunzio", "score": 0.91,
                             "woke": True, "ms": 420, "dur": 1.4, "audio": audio is not None, "verdict": "",
                             "correction": "", "note": "", "fix_speaker": "", "applied": False}
        if audio is not None:
            self.clips[ref] = audio

    def get(self, ref):
        return self.entries.get(ref)

    def audio(self, ref):
        return self.clips.get(ref)

    def feedback(self, ref, verdict, correction="", speaker="", note=""):
        self.verdicts[ref] = (verdict, correction, note)
        return ref in self.entries

    def delete(self, ref):
        self.clips.pop(ref, None)
        return self.entries.pop(ref, None) is not None

    def stats(self):
        return {"total": len(self.entries)}


class InteractionStoreTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "interactions.db"
        self.store = InteractionStore(self.path)

    def test_payload_is_encrypted_at_rest(self):
        self.store.add(Interaction(device="kiosk", channel="voice", said="accendi la luce segreta", reply="Fatto"))
        with sqlite3.connect(self.path) as conn:
            raw = b"".join(bytes(r[0]) for r in conn.execute("SELECT payload FROM interactions"))
        self.assertNotIn(b"segreta", raw)
        self.assertEqual(self.store.list()[0]["said"], "accendi la luce segreta")

    def test_filters_search_and_delete(self):
        first = self.store.add(Interaction(device="kiosk", channel="voice", said="che tempo fa", reply="Sole"))
        self.store.add(Interaction(device="kiosk", channel="text", said="scrivi una mail", reply="Ok"))
        self.assertEqual([i["said"] for i in self.store.list(channel="voice")], ["che tempo fa"])
        self.assertEqual(len(self.store.list(channel="")), 2)
        self.assertEqual([i["said"] for i in self.store.list(query="mail")], ["scrivi una mail"])
        self.assertTrue(self.store.delete(first))
        self.assertFalse(self.store.delete("not-an-id"))

    def test_rejects_invalid_channel_and_ref(self):
        self.assertEqual(self.store.add(Interaction(device="kiosk", channel="fax", said="x")), "")
        self.store.add(Interaction(device="kiosk", channel="voice", said="ciao", voice_ref="../../etc"))
        self.assertEqual(self.store.list()[0]["voice_ref"], "")


class TrailTests(unittest.TestCase):
    def test_voice_ref_reaches_remote_displays_only_when_valid(self):
        self.assertEqual(trail.heard_for("remote_display", {"voice_ref": "a1b2c3d4e5f6"}), {"voice_ref": "a1b2c3d4e5f6"})
        self.assertIsNone(trail.heard_for("remote_display", {"voice_ref": "zz"}))
        heard = trail.heard_for("kiosk", {"speaker": "Bad Slug!", "voice_ref": "a1b2c3d4e5f6", "followup": 1})
        self.assertEqual(heard["speaker"], "")
        self.assertTrue(heard["followup"])
        self.assertEqual(heard["voice_ref"], "a1b2c3d4e5f6")

    def test_only_page80_devices_are_recorded(self):
        self.assertEqual(trail.record("admin", "ciao", "ciao", {"reply": "ehi"}, None), "")


class VoiceLogServiceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.store = InteractionStore(Path(tmp.name) / "i.db")
        self.journal = FakeJournal()
        self.service = VoiceLogService(self.store, self.journal)
        now = time.time()
        self.journal.add("a1b2c3d4e5f6", now - 2, "accendi la luce", b"RIFF-audio")
        self.journal.add("0f0f0f0f0f0f", now - 3600, "vecchio comando", b"RIFF-old")
        self.linked = self.store.add(Interaction(device="kiosk", channel="voice", said="accendi la luce",
                                                 resolved="accendi la luce del salotto", reply="Fatto", intent="home",
                                                 voice_ref="a1b2c3d4e5f6", at=now))
        self.forged = self.store.add(Interaction(device="remote_display", channel="voice", said="altro",
                                                 voice_ref="0f0f0f0f0f0f", at=now))

    def test_list_joins_heard_text_and_hides_reference(self):
        items = {i["id"]: i for i in self.service.list(50, 0.0, "voice", "")}
        linked = items[self.linked]
        self.assertEqual(linked["heard"]["text"], "accendi la luce")
        self.assertEqual(linked["resolved"], "accendi la luce del salotto")
        self.assertNotIn("voice_ref", linked)
        self.assertIsNone(items[self.forged]["heard"])

    def test_audio_feedback_and_delete_require_a_valid_link(self):
        self.assertEqual(self.service.audio(self.linked), b"RIFF-audio")
        self.assertIsNone(self.service.audio(self.forged))
        self.assertTrue(self.service.feedback(self.linked, "wrong", "accendi la lampada", "parola sbagliata"))
        self.assertEqual(self.journal.verdicts["a1b2c3d4e5f6"][0], "wrong")
        self.assertFalse(self.service.feedback(self.forged, "ok", "", ""))
        self.assertTrue(self.service.delete(self.linked))
        self.assertNotIn("a1b2c3d4e5f6", self.journal.entries)


class StudioRoutesTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.store = StudioStore(db_path=root / "s.db")
        self.service = StudioService(store=self.store, smb=SmbStudioService(root_path=root / "smb"),
                                     memory=CrossMemoryService(store=self.store))
        self.seen = []

        async def fake(prompt, system, mode):
            self.seen.append((prompt, mode))
            return "risposta"

        self.service._execute_inference = fake
        api.service = self.service
        voice_api.voice_log = VoiceLogService(InteractionStore(root / "i.db"), FakeJournal())
        self.app = FastAPI()
        self.app.include_router(api.admin_routes)

    def client(self, authed: bool = True) -> TestClient:
        self.app.dependency_overrides = {require_admin: (lambda: "admin")} if authed else {}
        return TestClient(self.app)

    def test_no_public_routes_and_reads_need_admin(self):
        self.assertFalse(hasattr(api, "public_routes"))
        anonymous = self.client(False)
        for path in ("/api/ai_studio/threads", "/api/ai_studio/projects", "/api/ai_studio/memory/facts",
                     "/api/ai_studio/smb/tree", "/api/ai_studio/voice/turns"):
            self.assertEqual(anonymous.get(path).status_code, 401, path)
        self.assertEqual(self.client().get("/api/ai_studio/voice/turns").status_code, 200)

    def test_conversation_keeps_context_title_and_mode(self):
        client = self.client()
        th = client.post("/api/ai_studio/threads", json={"title": "Nuova Chat"}).json()
        client.post(f"/api/ai_studio/threads/{th['id']}/messages", json={"content": "Mi chiamo Ada e amo Rust"})
        client.post(f"/api/ai_studio/threads/{th['id']}/messages", json={"content": "Come mi chiamo?", "model_mode": "code"})
        self.assertIn("Mi chiamo Ada", self.seen[-1][0])
        self.assertEqual(self.seen[-1][1], "code")
        thread = self.service.store.get_thread(th["id"])
        self.assertEqual(thread.title, "Mi chiamo Ada e amo Rust")
        self.assertEqual(thread.model_mode, "code")
        bad = client.post(f"/api/ai_studio/threads/{th['id']}/messages", json={"content": "x", "model_mode": "evil"})
        self.assertEqual(bad.status_code, 400)

    def test_brain_failure_is_reported_not_faked(self):
        async def down(prompt, system, mode):
            raise StudioBrainUnavailable("nessun modello")

        self.service._execute_inference = down
        client = self.client()
        th = client.post("/api/ai_studio/threads", json={"title": "t"}).json()
        res = client.post(f"/api/ai_studio/threads/{th['id']}/messages", json={"content": "ciao"})
        self.assertEqual(res.status_code, 503)
        stream = client.post(f"/api/ai_studio/threads/{th['id']}/stream", json={"content": "ciao"})
        self.assertIn('"type": "error"', stream.text)
        self.assertNotIn('"type": "done"', stream.text)

    def test_unique_thread_ids_in_the_same_second(self):
        ids = {self.service.create_thread("Nuova Chat").id for _ in range(5)}
        self.assertEqual(len(ids), 5)

    def test_build_prompt_includes_history(self):
        prompt = asyncio.run(asyncio.sleep(0, build_prompt("ultima", [])))
        self.assertTrue(prompt.endswith("Richiesta utente: ultima"))


if __name__ == "__main__":
    unittest.main()
