import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from access import require_admin
from agenti.ai_studio import api
from agenti.ai_studio.inference_service import infer
from agenti.ai_studio.memory_service import CrossMemoryService
from agenti.ai_studio.service import StudioService
from agenti.ai_studio.smb_service import SmbStudioService
from agenti.ai_studio.store import StudioStore
from agenti.ai_studio.token_stream import StreamRelay, ThoughtSplitter, listening
from agenti.brain import llm, token_sink


def frames(text: str) -> list:
    return [json.loads(line[6:]) for line in text.splitlines() if line.startswith("data: ")]


class ThoughtSplitterTests(unittest.TestCase):
    def test_tags_split_across_chunks(self):
        splitter = ThoughtSplitter()
        out = []
        for chunk in ("<tho", "ught>pen", "so</th", "ought>Ciao", " <", "b>"):
            out += splitter.feed(chunk)
        out += splitter.flush()
        thought = "".join(t for k, t in out if k == "thought_delta")
        content = "".join(t for k, t in out if k == "token")
        self.assertEqual(thought, "penso")
        self.assertEqual(content, "Ciao <b>")

    def test_relay_reset_and_thinking_time(self):
        ticks = iter([1.0, 3.5, 3.6])
        queue = asyncio.Queue()
        relay = StreamRelay(queue, clock=lambda: next(ticks))
        relay.token("<thought>a")
        relay.token("</thought>b")
        relay.close()
        self.assertEqual(relay.thinking_ms(), 2500)
        relay.restart()
        events = [queue.get_nowait() for _ in range(queue.qsize())]
        self.assertEqual(events[-1], {"type": "reset"})
        self.assertEqual(relay.thinking_ms(), 0)


class BrainStreamTests(unittest.TestCase):
    def test_ollama_streams_tokens_only_when_a_sink_listens(self):
        lines = [{"response": "Ci"}, {"response": "ao"}, {"done": True, "eval_count": 2}]
        body = "\n".join(json.dumps(x) for x in lines).encode()
        seen = []
        transport = httpx.MockTransport(lambda request: (seen.append(json.loads(request.content)["stream"]),
                                                         httpx.Response(200, content=body))[1])
        real = httpx.AsyncClient

        class Sink:
            def __init__(self):
                self.tokens = []

            def token(self, text):
                self.tokens.append(text)

            def restart(self):
                self.tokens.clear()

        sink = Sink()
        with mock.patch.object(llm.httpx, "AsyncClient", lambda **kw: real(transport=transport, **kw)), \
                mock.patch.object(llm, "keep_alive", lambda m: "5m"), \
                mock.patch.object(llm, "_runtime_ollama_options", lambda *a: {}), \
                mock.patch.object(llm.usage_ledger, "record", lambda *a: None):
            with token_sink.feeding(sink):
                text = asyncio.run(llm._ollama("m", "p", "", False, 100, 0.1, 10))
        self.assertEqual(text, "Ciao")
        self.assertEqual(sink.tokens, ["Ci", "ao"])
        self.assertEqual(seen, [True])
        self.assertFalse(token_sink.active())

    def test_infer_feeds_the_listening_relay(self):
        async def fake_generate(prompt, **kw):
            token_sink.emit("<thought>x</thought>")
            token_sink.emit("ciao")
            return "<thought>x</thought>ciao"

        async def run():
            queue = asyncio.Queue()
            relay = StreamRelay(queue)
            with listening(relay):
                reply = await infer("p", "s", "fast")
            relay.close()
            return reply, [queue.get_nowait() for _ in range(queue.qsize())]

        with mock.patch.object(llm, "generate", fake_generate):
            reply, events = asyncio.run(run())
        self.assertEqual(reply, "<thought>x</thought>ciao")
        self.assertEqual(events, [{"type": "thought_delta", "token": "x"}, {"type": "token", "token": "ciao"}])


class StreamRouteTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        store = StudioStore(db_path=root / "st.db")
        self.service = StudioService(store=store, smb=SmbStudioService(root_path=root / "smb"),
                                     memory=CrossMemoryService(store=store))
        api.service = self.service
        app = FastAPI()
        app.include_router(api.admin_routes)
        app.dependency_overrides = {require_admin: (lambda: "admin")}
        self.client = TestClient(app)

    def test_tokens_arrive_before_done_and_reset_on_failover(self):
        async def fake_generate(prompt, **kw):
            token_sink.emit("sbagl")
            token_sink.restart()
            for piece in ("<thought>rif", "letto</thought>", "Ri", "sposta"):
                token_sink.emit(piece)
                await asyncio.sleep(0)
            return "<thought>riflettto</thought>Risposta"

        th = self.client.post("/api/ai_studio/threads", json={"title": "t"}).json()
        with mock.patch.object(llm, "generate", fake_generate):
            res = self.client.post(f"/api/ai_studio/threads/{th['id']}/stream", json={"content": "ciao"})
        events = frames(res.text)
        kinds = [e["type"] for e in events]
        self.assertEqual(kinds[0], "status")
        self.assertIn("reset", kinds)
        self.assertLess(kinds.index("reset"), kinds.index("thought_delta"))
        after = events[kinds.index("reset") + 1:]
        self.assertEqual("".join(e["token"] for e in after if e["type"] == "token"), "Risposta")
        self.assertEqual(kinds[-1], "done")
        self.assertEqual(events[-1]["message"]["content"], "Risposta")
        self.assertEqual(events[-1]["message"]["thought"], "riflettto")
        self.assertIsInstance(events[-1]["message"]["thinking_ms"], int)
        stored = self.service.store.list_messages(th["id"])[-1]
        self.assertEqual(stored.thinking_ms, events[-1]["message"]["thinking_ms"])


if __name__ == "__main__":
    unittest.main()
