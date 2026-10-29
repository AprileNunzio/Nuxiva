import ast
import asyncio
import json
import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from features.ear import broadcast, delivery
from features.ear.ingress import MAX_PENDING, RealtimeInput


class Socket:
    def __init__(self, blocked=False):
        self.messages = []
        self.closed = False
        self.gate = asyncio.Event()
        if not blocked:
            self.gate.set()

    async def send(self, data):
        await self.gate.wait()
        self.messages.append(json.loads(data))

    async def close(self, code=1000, reason=""):
        self.closed = True


class Client:
    def __init__(self, blocked=False, active=False):
        self.ws = Socket(blocked)
        self.last_pcm_time = time.time() if active else 0.0


class DeliveryTest(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self):
        for session in list(broadcast.SESSIONS):
            broadcast.unregister(session)
        await asyncio.sleep(0)

    async def test_slow_observer_does_not_delay_other_clients_or_producer(self):
        slow, fast = Client(blocked=True), Client()
        for client in (slow, fast):
            broadcast.register(client)
        start = time.monotonic()
        await broadcast.broadcast_event(fast, type="transcript", text="test")
        for _ in range(20):
            if fast.ws.messages:
                break
            await asyncio.sleep(0.002)
        self.assertLess(time.monotonic() - start, 0.15)
        self.assertEqual(fast.ws.messages[0]["text"], "test")
        self.assertFalse(slow.ws.messages)

    async def test_active_microphone_keeps_its_own_level_and_observer_gets_mirror(self):
        host, remote, observer = Client(), Client(active=True), Client()
        for client in (host, remote, observer):
            broadcast.register(client)
        await broadcast.broadcast_event(host, type="level", rms=0.8)
        await asyncio.sleep(0.01)
        self.assertFalse(remote.ws.messages)
        self.assertEqual(observer.ws.messages[0]["rms"], 0.8)
        self.assertFalse(observer.ws.messages[0]["origin"])
        await broadcast.broadcast_event(remote, type="level", rms=0.2)
        await asyncio.sleep(0.01)
        self.assertEqual(remote.ws.messages[0]["rms"], 0.2)
        self.assertNotIn("origin", remote.ws.messages[0])

    async def test_level_queue_coalesces_but_preserves_reliable_event_order(self):
        client = Client(blocked=True)
        broadcast.register(client)
        await broadcast.send_event(client, type="level", rms=0.1)
        await asyncio.sleep(0)
        for number in range(100):
            delivery.enqueue(client, "level", json.dumps({"type": "level", "rms": number}))
        delivery.enqueue(client, "wake", '{"type":"wake"}')
        delivery.enqueue(client, "transcript", '{"type":"transcript"}')
        self.assertLessEqual(len(client._ear_delivery.pending), 3)
        client.ws.gate.set()
        await asyncio.sleep(0.02)
        self.assertEqual([event["type"] for event in client.ws.messages][-2:], ["wake", "transcript"])
        self.assertIn(99, [event.get("rms") for event in client.ws.messages])

    async def test_reliable_queue_overflow_closes_only_the_slow_client(self):
        slow, healthy = Client(blocked=True), Client()
        broadcast.register(slow)
        broadcast.register(healthy)
        with self.assertLogs("nuxiva.ear.delivery", level="WARNING"):
            for _ in range(delivery.MAX_PENDING + 1):
                delivery.enqueue(slow, "state", '{"type":"state"}')
            await asyncio.sleep(0.01)
        self.assertTrue(slow.ws.closed)
        self.assertFalse(healthy.ws.closed)
        self.assertEqual(len(slow._ear_delivery.pending), 0)

    async def test_send_timeout_does_not_leave_an_unbounded_sender(self):
        client = Client(blocked=True)
        broadcast.register(client)
        with mock.patch.object(delivery, "SEND_TIMEOUT", 0.01), self.assertLogs("nuxiva.ear.delivery", level="WARNING"):
            await broadcast.send_event(client, type="state")
            await asyncio.wait_for(client._ear_delivery.task, 0.5)
        self.assertTrue(client.ws.closed)
        self.assertTrue(client._ear_delivery.task.done())


class RealtimeInputTest(unittest.IsolatedAsyncioTestCase):
    async def test_meter_remains_responsive_while_analysis_is_blocked(self):
        blocked, started = asyncio.Event(), asyncio.Event()
        readings, analyzed, resets = [], [], []

        async def analyze(pcm):
            started.set()
            await blocked.wait()
            analyzed.append(pcm)

        async def meter(rms):
            readings.append((time.monotonic(), rms))

        async def reset():
            resets.append(True)

        stream = RealtimeInput(analyze, meter, reset)
        try:
            await stream.feed(b"\x01\x00" * 480)
            await started.wait()
            start = time.monotonic()
            for value in range(10):
                await stream.feed(np.full(480, value, dtype="<i2").tobytes())
            self.assertLess(time.monotonic() - start, 0.15)
            self.assertEqual(len(readings), 11)
            self.assertEqual(len(analyzed), 0)
            self.assertLessEqual(len(stream.pending), MAX_PENDING)
            self.assertGreater(stream.dropped, 0)
            blocked.set()
            await asyncio.sleep(0.01)
            self.assertTrue(resets)
        finally:
            await stream.close()

    async def test_invalid_pcm_is_rejected_before_meter_or_analysis(self):
        analyze, meter, reset = mock.AsyncMock(), mock.AsyncMock(), mock.AsyncMock()
        stream = RealtimeInput(analyze, meter, reset)
        try:
            for pcm in (b"x", b"\x00" * 32002, "not binary"):
                with self.assertRaises(ValueError):
                    await stream.feed(pcm)
            meter.assert_not_awaited()
            analyze.assert_not_awaited()
        finally:
            await stream.close()

    async def test_raw_capture_updates_meter_without_enqueueing_analysis(self):
        analyze, meter = mock.AsyncMock(), mock.AsyncMock()
        stream = RealtimeInput(analyze, meter, mock.AsyncMock())
        try:
            await stream.feed(b"\x00\x00" * 480, analyze=False)
            meter.assert_awaited_once()
            analyze.assert_not_awaited()
            self.assertIsNone(stream.task)
        finally:
            await stream.close()

    async def test_analysis_error_is_reported_and_stream_can_recover(self):
        analyze = mock.AsyncMock(side_effect=[ValueError("bad frame"), None])
        reset = mock.AsyncMock()
        stream = RealtimeInput(analyze, mock.AsyncMock(), reset)
        try:
            with self.assertLogs("nuxiva.ear.ingress", level="ERROR"):
                await stream.feed(b"\x00\x00" * 480)
                await asyncio.sleep(0.01)
            await stream.feed(b"\x01\x00" * 480)
            await asyncio.sleep(0.01)
            self.assertEqual(analyze.await_count, 2)
            reset.assert_awaited_once()
        finally:
            await stream.close()

    async def test_actual_session_ingress_emits_meter_before_slow_frame_analysis(self):
        path = Path(__file__).resolve().parents[1] / "features" / "ear" / "service.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        session_node = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Session")
        namespace = {"asyncio": asyncio, "time": time, "np": np, "WAIT_FOR_SPEECH": 8, "FRAME": 480,
                     "LINK": {}, "SESSIONS": broadcast.SESSIONS, "broadcast_event": broadcast.broadcast_event}
        exec(compile(ast.Module(body=[session_node], type_ignores=[]), str(path), "exec"), namespace)
        session = namespace["Session"].__new__(namespace["Session"])
        session.page, session.raw = {"visible": "visible"}, None
        session.last_level, session.last_pcm_time, session.in_speech = 0, 0, False
        session.buffer, session.wake, session.ws = np.zeros(0, dtype=np.float32), SimpleNamespace(score=0), Socket()
        session._drop_caption = mock.AsyncMock()
        gate, started = asyncio.Event(), asyncio.Event()

        async def frame(_):
            started.set()
            await gate.wait()

        session._frame = frame
        session.input = RealtimeInput(session._process_pcm, session._meter, session._reset_input)
        broadcast.register(session)
        try:
            await session.feed(b"\x00\x01" * 480)
            await started.wait()
            await asyncio.sleep(0.11)
            await session.feed(b"\x00\x02" * 480)
            await asyncio.sleep(0.01)
            self.assertEqual(len(session.ws.messages), 2)
            self.assertGreater(session.ws.messages[1]["rms"], session.ws.messages[0]["rms"])
            self.assertGreater(time.time() - session.last_pcm_time, 0)
        finally:
            gate.set()
            await session.input.close()
            broadcast.unregister(session)
            await asyncio.sleep(0)


class WakeInferenceTest(unittest.IsolatedAsyncioTestCase):
    async def test_reset_during_inference_discards_the_stale_wake_result(self):
        ear = Path(__file__).resolve().parents[1] / "features" / "ear"
        if str(ear) not in sys.path:
            sys.path.append(str(ear))
        import wakeword
        with mock.patch.dict("os.environ", {"NUXIVA_WAKEWORD": "0"}):
            detector = wakeword.WakeWord()
        detector.model = object()

        def slow(_):
            time.sleep(0.1)
            return True

        with mock.patch.object(detector, "feed", side_effect=slow):
            task = asyncio.create_task(detector.detect(np.zeros(480, dtype=np.float32)))
            await asyncio.sleep(0.02)
            detector.request_reset()
            self.assertFalse(await task)

    async def test_slow_wake_inference_leaves_event_loop_available(self):
        ear = Path(__file__).resolve().parents[1] / "features" / "ear"
        if str(ear) not in sys.path:
            sys.path.append(str(ear))
        import wakeword
        with mock.patch.dict("os.environ", {"NUXIVA_WAKEWORD": "0"}):
            detector = wakeword.WakeWord()
        detector.model = object()

        def slow(_):
            time.sleep(0.2)
            return False

        ticks = 0
        with mock.patch.object(detector, "feed", side_effect=slow):
            task = asyncio.create_task(detector.detect(np.zeros(480, dtype=np.float32)))
            while not task.done():
                ticks += 1
                await asyncio.sleep(0.01)
            await task
        self.assertGreaterEqual(ticks, 8)
