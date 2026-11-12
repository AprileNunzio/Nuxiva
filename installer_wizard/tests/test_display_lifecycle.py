import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from agenti.desktop import lifecycle


class FakeEngine:

    def __init__(self):
        self.calls = []

    async def call(self, op, **fields):
        self.calls.append((op, fields))
        if op == "admit":
            return {"transitions": [{"instance": w["instance"], "screen": fields["screen"], "to": "warm"} for w in fields["widgets"]]}
        if op == "visibility":
            return {"transitions": [{"instance": fields["instance"], "screen": 0, "to": "live" if fields["visible"] else "frozen"}]}
        if op == "tick":
            return {"due": [{"instance": "music@1", "screen": 0}, {"instance": "other@1", "screen": 3}], "transitions": []}
        return {"transitions": []}


class CleanReportTests(unittest.TestCase):

    def test_only_valid_widgets_survive(self):
        data = lifecycle.clean_report({"screen": 1, "widgets": [
            {"instance": "music@1", "widget": "music", "refresh": 1, "visible": True, "cost_mb": 4},
            {"instance": "bad id", "widget": "x"}, {"instance": "a@1", "widget": "<script>"}, "junk",
            {"instance": "doc@1", "widget": "doc", "cost_mb": -5, "measured_mb": 1e9, "failed": True}]})
        self.assertEqual([w["instance"] for w in data["widgets"]], ["music@1", "doc@1"])
        self.assertEqual(data["widgets"][0]["cadence"], "live")
        self.assertEqual(data["widgets"][1]["cost_mb"], 0.0)
        self.assertEqual(data["costs"], {})
        self.assertEqual(data["errors"], ["doc@1"])

    def test_bad_screens_are_refused(self):
        for screen in (-1, 17, "0", None):
            with self.assertRaises(ValueError):
                lifecycle.clean_report({"screen": screen})

    def test_the_number_of_widgets_is_capped(self):
        many = [{"instance": f"w@{i}", "widget": "w"} for i in range(500)]
        self.assertEqual(len(lifecycle.clean_report({"widgets": many})["widgets"]), lifecycle.MAX_ITEMS)


class ReportTests(unittest.TestCase):

    def test_report_feeds_the_engine_and_returns_this_screen_only(self):
        engine = FakeEngine()
        out = asyncio.run(lifecycle.report(engine, {"screen": 0, "nucleus_only": True, "budget_mb": 256,
                                                    "widgets": [{"instance": "music@1", "widget": "music", "visible": True}]}))
        ops = [op for op, _ in engine.calls]
        self.assertEqual(ops[:2], ["audience", "admit"])
        self.assertIn("pressure", ops)
        self.assertEqual(ops[-1], "tick")
        self.assertEqual(out["states"], {"music@1": "live"})
        self.assertEqual(out["due"], ["music@1"])
        self.assertTrue(engine.calls[0][1]["nucleus_only"])


class SocketClientTests(unittest.IsolatedAsyncioTestCase):

    async def test_the_client_speaks_json_lines_over_the_unix_socket(self):
        seen = []

        async def serve(reader, writer):
            seen.append(json.loads(await reader.readline()))
            writer.write(b'{"ok": true, "data": {"pong": true}}\n')
            await writer.drain()
            writer.close()

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "d.sock"
            server = await asyncio.start_unix_server(serve, path=str(path))
            async with server:
                engine = lifecycle.DisplayEngine(path, timeout=2)
                self.assertEqual(await engine.call("ping"), {"pong": True})
        self.assertEqual(seen, [{"op": "ping"}])

    async def test_errors_from_the_engine_are_typed(self):
        async def serve(reader, writer):
            await reader.readline()
            writer.write(b'{"ok": false, "error": "display.scheduler.unknown_instance"}\n')
            await writer.drain()
            writer.close()

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "d.sock"
            server = await asyncio.start_unix_server(serve, path=str(path))
            async with server:
                with self.assertRaises(lifecycle.EngineRejected) as ctx:
                    await lifecycle.DisplayEngine(path).call("visibility", instance="x", visible=True)
        self.assertEqual(ctx.exception.code, "display.scheduler.unknown_instance")

    async def test_a_missing_engine_is_reported_as_unavailable(self):
        with self.assertRaises(lifecycle.EngineUnavailable):
            await lifecycle.DisplayEngine(Path("/nonexistent/display.sock"), timeout=0.5).call("ping")


if __name__ == "__main__":
    unittest.main()
