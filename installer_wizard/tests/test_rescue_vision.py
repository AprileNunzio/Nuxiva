import asyncio
import random
import unittest
from unittest import mock

import httpx
from fastapi import FastAPI
from starlette.testclient import TestClient

import native_core
from agenti.rescue import watch
from agenti.rescue.posture import PyPosture
from agenti.vision.posture import PostureWatch, bodies_of, router

NATIVE = native_core.symbol("RustPosture") is not None
FW, FH = 1280.0, 720.0


def standing(x=500.0):
    return (x, 120.0, 160.0, 480.0, 0.9, False)


def lying(x=420.0, rest=False):
    return (x, 480.0, 460.0, 150.0, 0.85, rest)


def frames(parts):
    out = []
    for start, end, every, body in parts:
        t = start
        while t <= end:
            out.append((t, [body]))
            t += every
    return out


def kinds(engine, timeline, camera="cam"):
    return [e[2] for t, b in timeline for e in engine.observe(camera, t, FW, FH, b)]


class PostureFallbackTest(unittest.TestCase):
    def test_fall_then_immobility(self):
        found = kinds(PyPosture(), frames([(0, 5, 1.2, standing()), (6, 80, 1.2, lying())]))
        self.assertEqual(found.count("fall"), 1)
        self.assertEqual(found.count("immobility"), 1)

    def test_bed_and_standing_are_normal(self):
        self.assertEqual(kinds(PyPosture(), frames([(0, 3, 1.2, standing()), (10, 400, 1.2, lying(rest=True))])), [])
        self.assertEqual(kinds(PyPosture(), frames([(0, 600, 1.2, standing())])), [])

    def test_bad_config_and_input(self):
        with self.assertRaises(ValueError):
            PyPosture(immobile_s=1.0)
        with self.assertRaises(ValueError):
            PyPosture(unlock=1)
        p = PyPosture()
        self.assertEqual(p.observe("bad camera!", 1.0, FW, FH, [standing()]), [])
        self.assertEqual(p.observe("cam", float("nan"), FW, FH, [standing()]), [])
        with self.assertRaises(ValueError):
            p.observe("cam", 1.0, FW, FH, [standing()] * 500)


def random_timeline(seed):
    rnd = random.Random(seed)
    t, out = 0.0, []
    for _ in range(120):
        t += rnd.choice((0.4, 1.0, 1.2, 2.0, 7.0, 30.0))
        people = []
        for _ in range(rnd.randint(0, 3)):
            x = rnd.choice((100.0, 500.0, 900.0)) + rnd.uniform(-20, 20)
            pick = rnd.random()
            if pick < 0.45:
                people.append((x, 120.0 + rnd.uniform(-10, 10), 160.0, 480.0, rnd.random(), False))
            elif pick < 0.6:
                people.append((x, 300.0, 220.0, 260.0, rnd.random(), False))
            else:
                people.append((x - 80, 480.0, 460.0, 150.0, rnd.random(), rnd.random() < 0.3))
        out.append((round(t, 3), people))
    return out


@unittest.skipUnless(NATIVE, "modulo nativo assente")
class PostureParityTest(unittest.TestCase):
    def test_random_parity(self):
        cls = native_core.symbol("RustPosture")
        for seed in range(80):
            rust, python = cls(), PyPosture()
            for t, bodies in random_timeline(seed):
                a = rust.observe("cam", t, FW, FH, bodies)
                b = python.observe("cam", t, FW, FH, bodies)
                self.assertEqual(len(a), len(b), f"{seed}:{t}")
                for x, y in zip(a, b):
                    self.assertEqual(x[:3], y[:3])
                    for i in (3, 4, 5):
                        self.assertAlmostEqual(x[i], y[i], places=9)

    def test_native_rejects_bad_config(self):
        with self.assertRaises(ValueError):
            native_core.symbol("RustPosture")(immobile_s=1.0)


class VisionPostureTest(unittest.TestCase):
    def test_bodies_on_furniture(self):
        found = [{"label": "persona", "score": 0.9, "box": [100, 100, 300, 120]},
                 {"label": "divano", "score": 0.8, "box": [80, 90, 360, 160]},
                 {"label": "persona", "score": 0.8, "box": [800, 100, 100, 300]},
                 {"label": "tazza", "score": 0.7, "box": [10, 10, 5, 5]}]
        bodies = bodies_of(found)
        self.assertEqual(len(bodies), 2)
        self.assertTrue(bodies[0][5])
        self.assertFalse(bodies[1][5])

    def test_events_are_numbered_and_served(self):
        w = PostureWatch(prefer_native=False)
        rows = []
        for t, b in frames([(0, 5, 1.2, standing()), (6, 20, 1.2, lying())]):
            box = [{"label": "persona", "score": b[0][4], "box": list(b[0][:4])}]
            rows += w.observe(box, 1280, 720, now=t)
        self.assertEqual([r["kind"] for r in rows], ["fall"])
        app = FastAPI()
        app.include_router(router(w))
        client = TestClient(app)
        body = client.get("/posture", params={"since": 0}).json()
        self.assertEqual(body["last"], 1)
        self.assertEqual(len(body["events"]), 1)
        self.assertEqual(client.get("/posture", params={"since": 1}).json()["events"], [])
        self.assertEqual(client.get("/posture", params={"since": -1}).status_code, 422)


class RescueWatchTest(unittest.TestCase):
    def test_ingest_feeds_coordinator_once(self):
        v = watch.VisionWatch(clock=lambda: 100.0)
        events = [{"seq": 1, "kind": "fall", "probability": 0.8, "confidence": 0.7, "camera": "vision:main", "at": 90.0},
                  {"seq": 2, "kind": "unlock", "probability": 1, "confidence": 1, "camera": "x", "at": 90.0},
                  {"seq": 3, "kind": "immobility", "probability": 0.7, "confidence": 0.7, "camera": "vision:main", "at": 9e9}]
        with mock.patch.object(watch.coordinator, "observe") as observe:
            self.assertEqual(v.ingest(events, 100.0), 2)
            self.assertEqual(v.ingest(events, 100.0), 0)
        self.assertEqual(observe.call_args_list[0].args[:4], ("fall", 0.8, 0.7, "vision:main"))
        self.assertEqual(observe.call_args_list[1].kwargs["at"], 100.0)

    def test_poll_resets_after_vision_restart(self):
        v = watch.VisionWatch(clock=lambda: 50.0)
        v.seq = 40
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"events": [], "last": 2}))

        async def go():
            async with httpx.AsyncClient(transport=transport) as client:
                return await v.poll(client)

        self.assertEqual(asyncio.run(go()), 0)
        self.assertEqual(v.seq, 0)


if __name__ == "__main__":
    unittest.main()
