import json
import unittest

from fastapi.testclient import TestClient

import auth
import nuxiva_supervisor
from features.hands import native, store

HEADERS = {"X-Nuxiva-Request": "1"}
POINTS = [[0.5, 0.5, 0.0]] * 21


def display_socket(path: str):
    public = TestClient(nuxiva_supervisor.public)
    public.cookies.set(auth.DISPLAY_COOKIE, auth.issue("display"))
    return public.websocket_connect(path, headers={"origin": "http://testserver", "host": "testserver"})


def frame(t: int, hands: list | None = None) -> str:
    return json.dumps({"t": t, "hands": hands if hands is not None else [{"handedness": "right", "points": POINTS}]})


@unittest.skipUnless(native.available(), "nuxiva_native non installato")
class HandsEngineApiTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(nuxiva_supervisor.admin)
        self.client.post("/api/auth/login", json={"username": "admin", "password": "nuxiva"}, headers=HEADERS)
        self.client.post("/api/hands/profile/reset", headers=HEADERS)

    def test_requires_auth_and_csrf(self):
        anonymous = TestClient(nuxiva_supervisor.admin)
        self.assertEqual(anonymous.get("/api/hands/profile").status_code, 401)
        self.assertEqual(self.client.put("/api/hands/profile", json={}).status_code, 403)

    def test_profile_view_has_catalog_and_defaults(self):
        view = self.client.get("/api/hands/profile").json()
        self.assertTrue(view["native"])
        self.assertIn("swipe.left", view["catalog"])
        self.assertAlmostEqual(view["profile"]["pinch_on"], 0.32, places=5)

    def test_save_validates_and_persists_encrypted(self):
        body = {"pinch_on": 0.28, "bindings": [{"gesture": "swipe.up", "action": "volume.up", "context": "tv"}]}
        saved = self.client.put("/api/hands/profile", json=body, headers=HEADERS)
        self.assertEqual(saved.status_code, 200)
        self.assertAlmostEqual(saved.json()["profile"]["pinch_on"], 0.28, places=5)
        self.assertNotIn(b"volume.up", store.SEALED.data_path.read_bytes())
        for bad in ({"pinch_on": 9}, {"bindings": [{"gesture": "pose.laser", "action": "x"}]}, {"nope": 1}, [1]):
            self.assertEqual(self.client.put("/api/hands/profile", json=bad, headers=HEADERS).status_code, 400)

    def test_socket_turns_landmarks_into_events(self):
        with display_socket("/api/hands/ws?context=desktop") as ws:
            ws.send_text(frame(0))
            events = json.loads(ws.receive_text())
        self.assertEqual(events[0]["type"], "pointer")
        self.assertEqual(events[0]["phase"], "move")

    def test_socket_ignores_garbage_and_switches_context(self):
        with display_socket("/api/hands/ws") as ws:
            ws.send_text("not json")
            ws.send_text(json.dumps({"t": 1, "hands": [{"points": [[0, 0, 0]]}]}))
            ws.send_text('{"context":"tv"}')
            ws.send_text(frame(2))
            self.assertEqual(json.loads(ws.receive_text())[0]["type"], "pointer")


class HandsSocketGuardTest(unittest.TestCase):
    def test_rejects_foreign_origin_and_missing_cookie(self):
        public = TestClient(nuxiva_supervisor.public)
        for headers in ({"origin": "http://evil.example", "host": "testserver"}, {"origin": "http://testserver", "host": "testserver"}):
            with self.assertRaises(Exception):
                with public.websocket_connect("/api/hands/ws", headers=headers) as ws:
                    ws.send_text(frame(0))
                    ws.receive_text()


class HandsEngineFallbackTest(unittest.TestCase):
    def test_catalog_empty_without_native(self):
        if native.available():
            self.assertTrue(native.catalog())
        else:
            self.assertEqual(native.catalog(), [])


if __name__ == "__main__":
    unittest.main()
