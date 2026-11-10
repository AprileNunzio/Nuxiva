import asyncio
import json
import unittest
from contextlib import aclosing
from unittest.mock import patch

from fastapi.responses import JSONResponse

from features.chat import api, streaming, turns
from features.nodes import assist_turn


class ChatTurnTests(unittest.IsolatedAsyncioTestCase):
    async def test_satellite_stop_is_bound_to_authenticated_node_and_request(self):
        ready = asyncio.Event()
        release = asyncio.Event()
        first_id, second_id = "a" * 32, "b" * 32

        async def operation():
            ready.set()
            await release.wait()
            return {"reply": "done"}

        first = asyncio.create_task(assist_turn.run("desktop", first_id, operation))
        second = asyncio.create_task(assist_turn.run("desktop", second_id, operation))
        await ready.wait()
        try:
            self.assertFalse(assist_turn.stop("other", first_id))
            self.assertTrue(assist_turn.stop("desktop", first_id))
            self.assertEqual(await first, {"cancelled": True})
            self.assertFalse(second.done())
        finally:
            release.set()
            await asyncio.gather(first, second)
        self.assertEqual(second.result(), {"reply": "done"})

    async def test_stop_is_scoped_to_one_owned_turn(self):
        principal = ("user", "owner")
        ready = asyncio.Queue()
        release = asyncio.Event()

        async def run(turn_id):
            token = turns.owner.set(principal)
            try:
                with turns.running(turn_id) as turn:
                    ready.put_nowait(turn_id)
                    try:
                        await release.wait()
                    except asyncio.CancelledError:
                        self.assertTrue(turn.stopping)
                        return "cancelled"
                    return "done"
            finally:
                turns.owner.reset(token)

        first = asyncio.create_task(run("first"))
        second = asyncio.create_task(run("second"))
        await ready.get()
        await ready.get()
        try:
            self.assertFalse(turns.stop("first", ("user", "other")))
            self.assertFalse(turns.stop("first", None))
            self.assertTrue(turns.stop("first", principal))
            self.assertTrue(turns.stop("first", principal))
            self.assertEqual(await first, "cancelled")
            self.assertFalse(turns.controllable("first", principal))
            self.assertFalse(second.done())
        finally:
            release.set()
            await asyncio.gather(first, second)
        self.assertEqual(second.result(), "done")

    async def test_stream_discards_queued_tokens_when_turn_stops(self):
        principal = ("user", "owner")
        ready = asyncio.Event()

        async def chat(*args):
            with turns.running("turn") as turn:
                streaming.push({"type": "token", "t": "first"})
                try:
                    await ready.wait()
                except asyncio.CancelledError:
                    self.assertTrue(turn.stopping)
                    streaming.push({"type": "token", "t": "late"})
                    return JSONResponse({"cancelled": True})

        with patch.object(api, "assistant_chat", chat):
            stream = api._stream_chat("question", "kiosk", None, None, owner=principal)
            async with aclosing(stream):
                self.assertEqual(json.loads((await anext(stream)).removeprefix("data: "))["t"], "first")
                self.assertTrue(turns.stop("turn", principal))
                events = [json.loads(line.removeprefix("data: ")) async for line in stream]
        self.assertEqual(events, [{"type": "done", "cancelled": True}])
