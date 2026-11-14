import asyncio
import json
import os
import unittest
from unittest import mock

from agenti.chat import duplex_feed, interrupt
from agenti.voices import duplex_api, duplex_voice


class Rig:
    def __init__(self, delay=0.0):
        self.json, self.bytes = [], []
        self.delay = delay
        self.synth_calls = []
        self.session = duplex_voice.VoiceSession("kiosk", self.send_json, self.send_bytes, self.synth)

    async def send_json(self, doc):
        self.json.append(doc)

    async def send_bytes(self, data):
        self.bytes.append(data)

    async def synth(self, text):
        self.synth_calls.append(text)
        await asyncio.sleep(self.delay)
        return b"RIFF" + text.encode()

    async def settle(self, rounds=60):
        for _ in range(rounds):
            await asyncio.sleep(0.01)

    def kinds(self):
        return [d["type"] for d in self.json]


def run(coro):
    return asyncio.run(coro)


class StreamingTest(unittest.TestCase):
    def setUp(self):
        interrupt.clear()
        self.addCleanup(interrupt.clear)

    def test_tokens_become_ordered_audio_frames(self):
        async def go():
            rig = Rig()
            feed = await rig.session.begin()
            for token in ("Ciao, sono ", "Nuxiva. ", "Come ", "stai", "? "):
                feed.put(token)
            feed.close()
            await rig.settle()
            return rig
        rig = run(go())
        chunks = [d for d in rig.json if d["type"] == "chunk"]
        self.assertGreaterEqual(len(chunks), 2)
        self.assertEqual([c["seq"] for c in chunks], list(range(1, len(chunks) + 1)))
        self.assertEqual(len(rig.bytes), len(chunks))
        gen, seq = duplex_voice.HEADER.unpack(rig.bytes[0][:8])
        self.assertEqual((gen, seq), (chunks[0]["gen"], 1))
        self.assertEqual(rig.kinds()[0], "reply_start")
        self.assertEqual(rig.kinds()[-1], "reply_end")

    def test_say_message_speaks_the_text(self):
        async def go():
            rig = Rig()
            await rig.session.handle(json.dumps({"type": "say", "text": "Buongiorno a tutti. Come va?"}))
            await rig.settle()
            return rig
        rig = run(go())
        self.assertTrue(rig.bytes)
        self.assertIn("reply_end", rig.kinds())

    def test_cut_stops_audio_and_remembers_the_unspoken_part(self):
        async def go():
            rig = Rig(delay=0.02)
            feed = await rig.session.begin()
            feed.put("Prima frase completa qui. ")
            feed.put("Seconda frase che non verra detta. ")
            feed.put("Terza frase ancora piu lunga. ")
            await rig.settle(8)
            first = [d for d in rig.json if d["type"] == "chunk"][0]
            rig.session.acknowledge(first["gen"], first["seq"])
            report = await rig.session.cut()
            before = len(rig.bytes)
            feed.put("Altro testo dopo il taglio. ")
            await rig.settle(20)
            return rig, report, before
        rig, report, before = run(go())
        self.assertEqual(report["state"], "interrupted")
        self.assertIn("cut", rig.kinds())
        self.assertEqual(len(rig.bytes), before)
        self.assertNotIn("reply_end", rig.kinds())
        entry = interrupt._entries["kiosk"]
        self.assertIn("Prima frase", entry["spoken"])
        self.assertIn("Seconda frase", entry["unspoken"])
        self.assertNotIn("Altro testo", entry["unspoken"])

    def test_cut_without_a_reply_is_a_no_op(self):
        async def go():
            return await Rig().session.cut()
        self.assertIsNone(run(go()))

    def test_stale_synthesis_is_never_sent_after_a_cut(self):
        async def go():
            rig = Rig(delay=0.15)
            feed = await rig.session.begin()
            feed.put("Una frase abbastanza lunga da sintetizzare. ")
            await rig.settle(3)
            await rig.session.cut()
            await rig.settle(30)
            return rig
        rig = run(go())
        self.assertEqual(rig.bytes, [])

    def test_new_reply_after_a_cut_gets_a_new_generation(self):
        async def go():
            rig = Rig()
            await rig.session.handle(json.dumps({"type": "say", "text": "Prima risposta lunga abbastanza. "}))
            await rig.settle(3)
            await rig.session.handle(json.dumps({"type": "cut"}))
            gen_a = rig.session.epoch
            await rig.session.handle(json.dumps({"type": "say", "text": "Seconda risposta lunga abbastanza. "}))
            await rig.settle(20)
            return rig, gen_a
        rig, gen_a = run(go())
        self.assertGreater(rig.session.epoch, gen_a)
        self.assertTrue(any(d["type"] == "chunk" and d["gen"] == rig.session.epoch for d in rig.json))

    def test_hostile_messages_are_ignored(self):
        async def go():
            rig = Rig()
            for raw in ("x" * 9000, "not json", "[1]", json.dumps({"type": "say", "text": "   "}), json.dumps({"type": "played", "gen": "a", "seq": 1}),
                        json.dumps({"type": "nope"})):
                await rig.session.handle(raw)
            return rig
        rig = run(go())
        self.assertEqual(rig.json, [])
        self.assertEqual(rig.synth_calls, [])

    def test_ack_is_idempotent_and_bounded_to_known_chunks(self):
        async def go():
            rig = Rig()
            await rig.session.handle(json.dumps({"type": "say", "text": "Frase uno abbastanza lunga. "}))
            await rig.settle(15)
            first = [d for d in rig.json if d["type"] == "chunk"][0]
            for _ in range(3):
                rig.session.acknowledge(first["gen"], first["seq"])
            rig.session.acknowledge(first["gen"], 999)
            rig.session.acknowledge(first["gen"] + 5, 1)
            return rig
        rig = run(go())
        self.assertEqual(rig.session.played, {1})

    def test_session_registry_is_bounded(self):
        saved = dict(duplex_voice._sessions)
        self.addCleanup(lambda: (duplex_voice._sessions.clear(), duplex_voice._sessions.update(saved)))
        duplex_voice._sessions.clear()
        rig = Rig()
        for index in range(duplex_voice.MAX_SESSIONS):
            self.assertTrue(duplex_voice.attach(f"d{index}", rig.session))
        self.assertFalse(duplex_voice.attach("extra", rig.session))
        self.assertTrue(duplex_voice.attach("d0", rig.session))
        duplex_voice.detach("d0", rig.session)
        self.assertIsNone(duplex_voice.session_for("d0"))


class ModeTest(unittest.TestCase):
    def test_legacy_is_the_default(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NUXIVA_DUPLEX", None)
            self.assertFalse(duplex_voice.enabled())
        with mock.patch.dict(os.environ, {"NUXIVA_DUPLEX": "rust"}):
            self.assertTrue(duplex_voice.enabled())

    def test_chat_hook_is_inert_in_legacy_mode(self):
        with mock.patch.dict(os.environ, {"NUXIVA_DUPLEX": "legacy"}):
            self.assertIsNone(run(duplex_feed.begin("kiosk")))
        duplex_feed.token(None, {"type": "token", "t": "x"})
        duplex_feed.close(None)

    def test_chat_hook_feeds_the_registered_session(self):
        async def go():
            rig = Rig()
            duplex_voice.attach("kiosk", rig.session)
            try:
                with mock.patch.dict(os.environ, {"NUXIVA_DUPLEX": "rust"}):
                    feed = await duplex_feed.begin("kiosk")
                duplex_feed.token(feed, {"type": "token", "t": "Risposta lunga abbastanza per parlare. "})
                duplex_feed.token(feed, {"type": "other", "t": "ignorato"})
                duplex_feed.close(feed)
                await rig.settle(20)
            finally:
                duplex_voice.detach("kiosk", rig.session)
            return rig
        rig = run(go())
        self.assertTrue(rig.bytes)
        self.assertNotIn("ignorato", " ".join(rig.synth_calls))

    def test_socket_trust_requires_local_or_same_origin_cookie(self):
        class Socket:
            def __init__(self, host, origin="", cookies=None):
                self.client = type("C", (), {"host": host})()
                self.headers = {"origin": origin, "host": "nuxiva.lan"}
                self.cookies = cookies or {}
        self.assertTrue(duplex_api.trusted(Socket("127.0.0.1")))
        self.assertFalse(duplex_api.trusted(Socket("10.0.0.9")))
        self.assertFalse(duplex_api.trusted(Socket("10.0.0.9", "http://evil.example")))


class InterruptTest(unittest.TestCase):
    def setUp(self):
        interrupt.clear()
        self.addCleanup(interrupt.clear)

    def test_continue_resumes_with_the_unspoken_text(self):
        interrupt.remember("kiosk", "Ho detto la prima parte.", "Questa e la seconda parte.", now=100.0)
        text = interrupt.context_for("kiosk", "continua", now=110.0)
        self.assertIn("Questa e la seconda parte.", text)
        self.assertIn("proseguire", text)

    def test_modify_asks_to_redo(self):
        interrupt.remember("kiosk", "Detto.", "Resto.", now=100.0)
        self.assertIn("rifare", interrupt.context_for("kiosk", "no aspetta, fallo più breve", now=105.0))

    def test_cancel_drops_it(self):
        interrupt.remember("kiosk", "Detto.", "Resto.", now=100.0)
        self.assertIn("lasciar stare", interrupt.context_for("kiosk", "lascia stare", now=105.0))
        self.assertFalse(interrupt.pending("kiosk", now=106.0))

    def test_unrelated_text_clears_without_instruction(self):
        interrupt.remember("kiosk", "Detto.", "Resto.", now=100.0)
        self.assertEqual(interrupt.context_for("kiosk", "che tempo fa domani a Roma", now=105.0), "")
        self.assertEqual(interrupt.context_for("kiosk", "continua", now=106.0), "")

    def test_expiry_and_device_isolation(self):
        interrupt.remember("kiosk", "Detto.", "Resto.", now=100.0)
        self.assertEqual(interrupt.context_for("altro", "continua", now=101.0), "")
        self.assertEqual(interrupt.context_for("kiosk", "continua", now=100.0 + interrupt.TTL_SECONDS + 1), "")

    def test_store_is_bounded_and_text_clipped(self):
        for index in range(interrupt.MAX_ENTRIES + 10):
            interrupt.remember(f"d{index}", "x" * 20000, "y" * 20000, now=100.0)
        self.assertEqual(len(interrupt._entries), interrupt.MAX_ENTRIES)
        self.assertEqual(len(next(iter(interrupt._entries.values()))["unspoken"]), interrupt.MAX_TEXT)
