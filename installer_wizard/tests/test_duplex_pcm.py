import asyncio
import json
import struct
import unittest

from agenti.chat import interrupt
from agenti.voices import duplex_voice


def wav(ms, rate=24000):
    samples = [i % 300 for i in range(rate * ms // 1000)]
    data = struct.pack(f"<{len(samples)}h", *samples)
    fmt = struct.pack("<HHIIHH", 1, 1, rate, rate * 2, 2, 16)
    return b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack("<I", 16) + fmt + b"data" + struct.pack("<I", len(data)) + data


class Rig:
    def __init__(self, ms=300, broken=False):
        self.json, self.bytes, self.ms, self.broken = [], [], ms, broken
        self.session = duplex_voice.VoiceSession("kiosk", self.send_json, self.send_bytes, self.synth)

    async def send_json(self, doc):
        self.json.append(doc)

    async def send_bytes(self, data):
        self.bytes.append(data)

    async def synth(self, text):
        return b"RIFF" + text.encode() if self.broken else wav(self.ms)

    async def settle(self, seconds):
        await asyncio.sleep(seconds)

    def kinds(self):
        return [d["type"] for d in self.json]


def run(coro):
    return asyncio.run(coro)


class PcmTest(unittest.TestCase):
    def setUp(self):
        interrupt.clear()
        self.addCleanup(interrupt.clear)

    def test_hello_switches_to_typed_pcm_frames(self):
        async def go():
            rig = Rig(ms=300)
            await rig.session.handle(json.dumps({"type": "hello", "version": 1, "pcm": True}))
            await rig.session.handle(json.dumps({"type": "say", "text": "Buongiorno a tutti, come va oggi?"}))
            await rig.settle(1.5)
            await rig.session.stop()
            return rig
        rig = run(go())
        chunks = [d for d in rig.json if d["type"] == "chunk"]
        self.assertTrue(chunks and all(c["pcm"] is True and c["rate"] == 24000 for c in chunks))
        declared = sum(c["frames"] for c in chunks)
        self.assertEqual(len(rig.bytes), declared)
        for frame in rig.bytes:
            self.assertEqual(frame[0], 1)
            gen, seq = struct.unpack(">II", frame[1:9])
            self.assertEqual(gen, chunks[0]["gen"])
            self.assertIn(seq, [c["seq"] for c in chunks])
            self.assertLessEqual(len(frame) - 9, 4096)
        self.assertEqual(rig.kinds()[-1], "reply_end")

    def test_reply_end_waits_for_the_audio_to_drain(self):
        async def go():
            rig = Rig(ms=600)
            await rig.session.handle(json.dumps({"type": "hello", "version": 1, "pcm": True}))
            await rig.session.handle(json.dumps({"type": "say", "text": "Una frase sola ma abbastanza lunga."}))
            await rig.settle(0.3)
            early = "reply_end" in rig.kinds()
            await rig.settle(1.5)
            return early, rig
        early, rig = run(go())
        self.assertFalse(early)
        self.assertIn("reply_end", rig.kinds())

    def test_without_hello_the_legacy_format_is_unchanged(self):
        async def go():
            rig = Rig(ms=100)
            await rig.session.handle(json.dumps({"type": "say", "text": "Buongiorno a tutti, come va oggi?"}))
            await rig.settle(0.5)
            return rig
        rig = run(go())
        chunk = next(d for d in rig.json if d["type"] == "chunk")
        self.assertNotIn("pcm", chunk)
        self.assertEqual(duplex_voice.HEADER.unpack(rig.bytes[0][:8])[0], chunk["gen"])

    def test_bad_hello_keeps_the_legacy_format(self):
        async def go():
            rig = Rig(ms=100)
            for doc in ({"type": "hello", "version": 2, "pcm": True}, {"type": "hello", "pcm": "yes"}, {"type": "hello"}):
                await rig.session.handle(json.dumps(doc))
                self.assertFalse(rig.session.pcm)
        run(go())

    def test_cut_drops_every_queued_frame_at_once(self):
        async def go():
            rig = Rig(ms=3000)
            await rig.session.handle(json.dumps({"type": "hello", "version": 1, "pcm": True}))
            await rig.session.handle(json.dumps({"type": "say", "text": "Una frase molto lunga che dura parecchi secondi."}))
            await rig.settle(0.4)
            sent_before = len(rig.bytes)
            report = await rig.session.cut()
            await rig.settle(0.4)
            return rig, sent_before, report
        rig, sent_before, report = run(go())
        self.assertIsNotNone(report)
        cut = next(d for d in rig.json if d["type"] == "cut")
        self.assertGreater(cut["dropped_ms"], 2000)
        self.assertEqual(len(rig.bytes), sent_before)
        self.assertLess(sent_before * 40, 1500)
        self.assertNotIn("reply_end", rig.kinds())

    def test_a_corrupt_wav_is_dropped_without_breaking_the_reply(self):
        async def go():
            rig = Rig(broken=True)
            await rig.session.handle(json.dumps({"type": "hello", "version": 1, "pcm": True}))
            await rig.session.handle(json.dumps({"type": "say", "text": "Buongiorno a tutti, come va oggi?"}))
            await rig.settle(0.5)
            return rig
        rig = run(go())
        self.assertEqual(rig.bytes, [])
        self.assertNotIn("chunk", rig.kinds())
        self.assertIn("reply_end", rig.kinds())
        self.assertEqual(rig.session.counts["chunks"], 0)


if __name__ == "__main__":
    unittest.main()
