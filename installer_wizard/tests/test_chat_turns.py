import asyncio
import json
import sys
import unittest
from contextlib import aclosing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.responses import JSONResponse

from agenti.chat import api, streaming, turns
from agenti.nodes import assist_turn
from agenti.nodes.assist_stop_store import AssistStopStore


class ChatTurnTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        folder = self.enterContext(TemporaryDirectory())
        self.stop_db = Path(folder) / "assist-stops.sqlite3"
        self.enterContext(patch.object(assist_turn, "_stops", AssistStopStore(self.stop_db)))

    async def test_separate_process_can_cancel_running_work(self):
        ready = asyncio.Event()
        stopped = asyncio.Event()
        turn_id = "d" * 32

        async def operation():
            ready.set()
            try:
                await asyncio.Future()
            finally:
                stopped.set()

        work = asyncio.create_task(assist_turn.run("desktop", turn_id, operation))
        await asyncio.wait_for(ready.wait(), 3)
        wizard = Path(__file__).resolve().parents[1]
        code = (
            "import sys; sys.path[:0] = sys.argv[3:]; "
            "from agenti.nodes.assist_stop_store import AssistStopStore; "
            "AssistStopStore(sys.argv[1]).record(sys.argv[2])"
        )
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-I", "-c", code, str(self.stop_db), f"node:desktop:{turn_id}",
                str(wizard), str(wizard / "backend"),
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), 10)
            self.assertEqual(proc.returncode, 0, stderr.decode(errors="replace"))
            self.assertEqual(await asyncio.wait_for(work, 3), {"cancelled": True})
            self.assertTrue(stopped.is_set())
        finally:
            if not work.done():
                work.cancel()
                await asyncio.gather(work, return_exceptions=True)

    async def test_stop_before_admission_skips_only_the_matching_node_request(self):
        turn_id = "c" * 32

        async def operation():
            return {"reply": "done"}

        self.assertFalse(await assist_turn.stop("first", turn_id))
        self.assertEqual(await assist_turn.run("first", turn_id, operation), {"cancelled": True})
        self.assertEqual(await assist_turn.run("second", turn_id, operation), {"reply": "done"})

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
            self.assertFalse(await assist_turn.stop("other", first_id))
            await assist_turn.stop("desktop", first_id)
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
