import asyncio
import json
import time
import unittest
from unittest import mock

import httpx

from agenti.brain.components import LimbicModulator
from agenti.chat import brain_chain, pace, streaming
from agenti.chat.journey_flow import ChatJourney
from agenti.cloud import client, pool, stream
from server.core.reasoning.engines.base import Strategy

GROQ = "cloud:groq/openai/gpt-oss-20b"
CLAUDE = "cloud:anthropic/claude-fable-5-2"


class Vault:
    def get(self, pid):
        return {"key": "k", "options": {}}

    def configured(self, pid):
        return True


def sse(events: list[dict], done: bool = True) -> bytes:
    lines = [f"data: {json.dumps(e)}\n\n" for e in events]
    if done:
        lines.append("data: [DONE]\n\n")
    return "".join(lines).encode()


class PaceTest(unittest.TestCase):
    def test_short_plain_questions_are_simple(self):
        self.assertTrue(pace.simple("quanto fa due più due?"))
        self.assertTrue(pace.simple("che ore sono"))

    def test_long_or_reasoning_questions_are_not_simple(self):
        self.assertFalse(pace.simple("spiegami la fotosintesi"))
        self.assertFalse(pace.simple("compare these two plans"))
        self.assertFalse(pace.simple(" ".join(["parola"] * 20)))

    def test_patience_follows_the_first_answer_within_bounds(self):
        self.assertEqual(pace.patience(15.0, 1.0), pace.PATIENCE_FLOOR_S)
        self.assertAlmostEqual(pace.patience(15.0, 10.0), 10.0 * pace.PATIENCE_RATIO)
        self.assertEqual(pace.patience(2.0, 60.0), 2.0)
        self.assertEqual(pace.patience(0.0, 5.0), 0.0)


class RaceTest(unittest.TestCase):
    def test_only_the_first_lane_reaches_the_stream(self):
        queue: asyncio.Queue = asyncio.Queue()
        race = streaming.Race()
        sink, contest = streaming.sink.set(queue), streaming.race.set(race)
        try:
            for lane, text in ((1, "a"), (0, "b"), (1, "c")):
                marker = streaming.lane.set(lane)
                streaming.token(text)
                streaming.lane.reset(marker)
            streaming.push({"type": "brain_route", "route": {}})
        finally:
            streaming.race.reset(contest)
            streaming.sink.reset(sink)
        events = [queue.get_nowait() for _ in range(queue.qsize())]
        self.assertEqual([e.get("t") for e in events if e["type"] == "token"], ["a", "c"])
        self.assertEqual(race.owner, 1)
        self.assertEqual(sum(1 for e in events if e["type"] == "brain_route"), 1)


def branch(delay: float, text: str, stream_first: bool = False):
    async def run(query, context, limbic):
        if stream_first:
            streaming.token(text[:3])
        await asyncio.sleep(delay)
        return {"text": text, "confidence": brain_chain.CONFIDENCE_OK}
    return run


class ParallelTest(unittest.TestCase):
    def setUp(self):
        self.chain = brain_chain.CorticalBrainChain()
        self.chain.limbic = LimbicModulator()
        floor = mock.patch.object(pace, "PATIENCE_FLOOR_S", 0.05)
        floor.start()
        self.addCleanup(floor.stop)

    def test_slow_candidates_no_longer_hold_the_answer(self):
        plan = Strategy(kind="deep", candidates=2, pick="best", critic=False, wait_s=15.0)
        started = time.monotonic()
        answers = asyncio.run(self.chain._parallel("q", {}, [branch(0.05, "veloce"), branch(3.0, "lento")], plan, []))
        self.assertLess(time.monotonic() - started, 1.0)
        self.assertEqual([a["text"] for a in answers], ["veloce"])

    def test_streaming_keeps_the_candidate_that_spoke_first(self):
        plan = Strategy(kind="deep", candidates=2, pick="first", critic=False, wait_s=0.0)

        async def go():
            queue: asyncio.Queue = asyncio.Queue()
            marker = streaming.sink.set(queue)
            try:
                answers = await self.chain._parallel("q", {}, [branch(0.3, "lento", True), branch(0.05, "muto")], plan, [])
            finally:
                streaming.sink.reset(marker)
            return answers, [queue.get_nowait()["t"] for _ in range(queue.qsize())]

        answers, tokens = asyncio.run(go())
        self.assertEqual([a["text"] for a in answers], ["lento"])
        self.assertEqual(tokens, ["len"])

    def test_competitors_are_cancelled_once_a_lane_owns_the_stream(self):
        plan = Strategy(kind="deep", candidates=2, pick="first", critic=False, wait_s=0.0)
        finished = []

        def tracked(delay, text, first):
            async def run(query, context, limbic):
                if first:
                    streaming.token(text)
                await asyncio.sleep(delay)
                finished.append(text)
                return {"text": text, "confidence": brain_chain.CONFIDENCE_OK}
            return run

        async def go():
            marker = streaming.sink.set(asyncio.Queue())
            try:
                return await self.chain._parallel("q", {}, [tracked(0.1, "primo", True), tracked(0.5, "secondo", False)], plan, [])
            finally:
                streaming.sink.reset(marker)

        answers = asyncio.run(go())
        self.assertEqual([a["text"] for a in answers], ["primo"])
        self.assertEqual(finished, ["primo"])


class CloudStreamTest(unittest.TestCase):
    def run_stream(self, ref: str, handler, fallback=None):
        tokens: list[str] = []

        async def go():
            transport = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            try:
                with mock.patch.object(client, "vault", Vault()), mock.patch.object(stream, "shared", lambda: transport), \
                        mock.patch.object(stream, "complete", fallback or mock.AsyncMock()):
                    return await stream.complete_stream(ref, [{"role": "user", "content": "x"}], "s", 200, 0.2, tokens.append)
            finally:
                await transport.aclose()

        return asyncio.run(go()), tokens

    def test_openai_compatible_tokens_are_forwarded_as_they_arrive(self):
        seen = {}

        def handler(request):
            seen.update(json.loads(request.content))
            return httpx.Response(200, content=sse([{"choices": [{"delta": {"content": "Cia"}}]},
                                                    {"choices": [{"delta": {"content": "o!"}}]},
                                                    {"choices": [], "usage": {"prompt_tokens": 3, "completion_tokens": 2}}]))

        answer, tokens = self.run_stream(GROQ, handler)
        self.assertTrue(seen["stream"])
        self.assertEqual(tokens, ["Cia", "o!"])
        self.assertEqual((answer.text, answer.tokens), ("Ciao!", 2))

    def test_anthropic_text_deltas_are_streamed_and_thinking_is_skipped(self):
        events = [{"type": "message_start", "message": {"usage": {"input_tokens": 4}}},
                  {"type": "content_block_delta", "delta": {"type": "thinking_delta", "thinking": "hmm"}},
                  {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Buon"}},
                  {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "giorno"}},
                  {"type": "message_delta", "usage": {"output_tokens": 7}}]
        answer, tokens = self.run_stream(CLAUDE, lambda request: httpx.Response(200, content=sse(events, done=False)))
        self.assertEqual(tokens, ["Buon", "giorno"])
        self.assertEqual((answer.text, answer.tokens), ("Buongiorno", 7))

    def test_provider_rejecting_streaming_falls_back_to_a_single_reply(self):
        fallback = mock.AsyncMock(return_value=client.Reply(text="intera", model=GROQ, ms=1.0))
        answer, tokens = self.run_stream(GROQ, lambda request: httpx.Response(400, json={"error": "no stream"}), fallback)
        self.assertEqual((answer.text, tokens), ("intera", ["intera"]))
        fallback.assert_awaited_once()

    def test_errors_and_garbage_are_reported_not_hidden(self):
        with self.assertRaises(client.CloudError):
            self.run_stream(GROQ, lambda request: httpx.Response(401, json={"error": {"message": "bad key"}}))
        with self.assertRaises(client.CloudError):
            self.run_stream(GROQ, lambda request: httpx.Response(200, content=b"data: {broken\n\n"))
        with self.assertRaises(client.CloudError):
            self.run_stream(CLAUDE, lambda request: httpx.Response(200, content=sse([{"type": "error", "error": {"message": "x"}}])))


class PoolTest(unittest.TestCase):
    def test_one_client_per_loop_is_reused(self):
        async def go():
            first, second = pool.shared(), pool.shared()
            await pool.close()
            return first is second, first.is_closed

        self.assertEqual(asyncio.run(go()), (True, True))

    def test_anthropic_model_limit_is_asked_once(self):
        calls = []

        def handler(request):
            calls.append(request.url.path)
            return httpx.Response(200, json={"max_tokens": 64000})

        async def go():
            transport = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            try:
                with mock.patch.object(client, "shared", lambda: transport), mock.patch.dict(client._model_limits, clear=True):
                    return [await client._anthropic_model_limit("https://a.test/v1", "m", {}) for _ in range(3)]
            finally:
                await transport.aclose()

        self.assertEqual(asyncio.run(go()), [64000] * 3)
        self.assertEqual(len(calls), 1)


class TimingsTest(unittest.TestCase):
    def test_phases_are_the_steps_under_the_orchestrator(self):
        flow = ChatJourney("ciao", "ciao", "test", "utente")
        flow.begin()
        tracker = flow.tracker
        ceo = tracker.add_node("ceo", "CEO Orchestrator", parent=flow.memory)
        quick = tracker.add_node("classifier", "Classificatore", parent=ceo)
        model = tracker.add_node("system2", "Generazione della risposta", parent=ceo)
        tracker.nodes[model]["a"], tracker.nodes[model]["b"] = 0.2, 1.4
        tracker.nodes[quick]["a"], tracker.nodes[quick]["b"] = 0.1, 0.11
        flow.answered({"reply": "ok"})
        timings = flow.timings()
        self.assertEqual([(p["kind"], p["ms"]) for p in timings["phases"]], [("system2", 1200)])
        self.assertGreaterEqual(timings["total_ms"], 0)

    def test_internal_turns_have_no_timings(self):
        self.assertEqual(ChatJourney("x", "x", "test", "utente", internal=True).timings(), {})


if __name__ == "__main__":
    unittest.main()
