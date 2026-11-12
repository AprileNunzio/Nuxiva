import json
import unittest
from unittest import mock

import display_events
import snapshot
import stream_delta
from state import store

CASES = [
    ({"a": 1}, {"a": 1}),
    ({"a": 1, "b": {"c": 2, "d": [1, 2]}, "gone": True}, {"a": 1, "b": {"c": 3, "d": [2]}, "new": None}),
    ({"a": None}, {}),
    ({"a/b": {"c~d": 1}}, {"a/b": {"c~d": 2}}),
    ({"a": {"x": 1}}, {"a": "text"}),
    ({"n": 1}, {"n": True}),
]


def unescape(token):
    return token.replace("~1", "/").replace("~0", "~")


def apply(doc, ops):
    for op in ops:
        parts = [unescape(t) for t in op["path"].split("/")[1:]] if op["path"] else []
        if not parts:
            doc = op["value"]
            continue
        node = doc
        for part in parts[:-1]:
            node = node[part]
        if op["op"] == "remove":
            del node[parts[-1]]
        else:
            node[parts[-1]] = op["value"]
    return doc


class PythonDiffTests(unittest.TestCase):

    def test_python_diff_roundtrips(self):
        for old, new in CASES:
            ops = json.loads(stream_delta.python_diff(json.dumps(old), json.dumps(new)))
            self.assertEqual(apply(json.loads(json.dumps(old)), ops), new)

    def test_native_and_python_agree(self):
        if stream_delta.NATIVE is None:
            self.skipTest("nuxiva_native non installato")
        for old, new in CASES:
            a, b = json.dumps(old), json.dumps(new)
            native = json.loads(stream_delta.NATIVE(a, b))
            self.assertEqual(apply(json.loads(a), native), new)
            self.assertEqual(sorted(map(json.dumps, native)), sorted(map(json.dumps, json.loads(stream_delta.python_diff(a, b)))))

    def test_huge_changes_fall_back_to_a_full_frame(self):
        old = json.dumps({str(i): i for i in range(stream_delta.MAX_OPS + 5)})
        new = json.dumps({str(i): -i for i in range(stream_delta.MAX_OPS + 5)})
        self.assertIsNone(stream_delta.python_diff(old, new))


class FrameTests(unittest.TestCase):

    def setUp(self):
        self.cache = stream_delta.DeltaCache(stream_delta.python_diff)
        self.one = stream_delta.Build(1, json.dumps({"a": 1, "big": "x" * 200}))
        self.two = stream_delta.Build(2, json.dumps({"a": 2, "big": "x" * 200}))

    def test_first_frame_is_full(self):
        frame = json.loads(stream_delta.frame(self.cache, None, self.one, []))
        self.assertEqual((frame["t"], frame["v"], frame["s"]["a"]), ("full", 1, 1))

    def test_following_frames_are_small_patches(self):
        frame = json.loads(stream_delta.frame(self.cache, self.one, self.two, []))
        self.assertEqual(frame, {"t": "patch", "f": 1, "v": 2, "p": [{"op": "replace", "path": "/a", "value": 2}]})

    def test_nothing_new_sends_nothing(self):
        self.assertIsNone(stream_delta.frame(self.cache, self.one, self.one, []))

    def test_events_travel_even_without_changes(self):
        frame = json.loads(stream_delta.frame(self.cache, self.one, self.one, [{"k": "holo_action", "p": {"express": "smile"}}]))
        self.assertEqual(frame["e"], [{"k": "holo_action", "p": {"express": "smile"}}])

    def test_patches_are_computed_once_for_every_client(self):
        differ = mock.Mock(return_value="[]")
        cache = stream_delta.DeltaCache(differ)
        cache.ops(self.one, self.two)
        cache.ops(self.one, self.two)
        differ.assert_called_once()


class DeltaStreamTests(unittest.TestCase):

    def setUp(self):
        snapshot._shared.clear()

    def test_a_screen_rebuilds_the_exact_state_from_patches(self):
        states = iter([{"a": 1, "b": {"c": 1}}, {"a": 1, "b": {"c": 2}}, {"a": 3}])
        events = display_events.DisplayEvents()
        with mock.patch.object(snapshot, "full_snapshot", side_effect=lambda admin: next(states)), \
                mock.patch.object(display_events, "events", events):
            text, before, cursor = snapshot.delta_frame(False, None, 0)
            state = json.loads(text)["s"]
            for _ in range(2):
                store.touch()
                text, before, cursor = snapshot.delta_frame(False, before, cursor)
                frame = json.loads(text)
                if frame["t"] == "patch":
                    state = apply(state, frame["p"])
                else:
                    state = frame["s"]
        self.assertEqual(state, {"a": 3})

    def test_the_delta_endpoint_is_public(self):
        from fastapi.testclient import TestClient
        from system_api import public_routes
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(public_routes)
        paths = {r.path for r in app.routes}
        self.assertIn("/api/stream/delta", paths)
        self.assertTrue(TestClient)


if __name__ == "__main__":
    unittest.main()
