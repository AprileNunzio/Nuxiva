import tempfile
import unittest
from pathlib import Path
from unittest import mock

import httpx
from fastapi.testclient import TestClient

import nuxiva_supervisor
import setup_api
import setup_face
import setup_session
from setup_session import session_manager

HEADERS = {"X-Nuxiva-Request": "1"}
FRAME = b"\xff\xd8\xff\xe0" + b"0" * 2000


class SetupFaceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.local = True
        self.patches = [mock.patch.object(setup_session, "SESSION_FILE", Path(self.tmp.name) / "session.json"),
                        mock.patch.object(setup_api, "_private_client", lambda r: True),
                        mock.patch.object(setup_face, "is_local", lambda r: self.local)]
        for p in self.patches:
            p.start()
        setup_api.SETUP_FILE.unlink(missing_ok=True)
        session_manager.reset()
        session_manager.config.update(owner_name="Nunzio", owner_last="Aprile")
        self.calls = []
        self.client = TestClient(nuxiva_supervisor.public)

    def tearDown(self):
        for p in self.patches:
            p.stop()
        session_manager.reset()
        self.tmp.cleanup()

    def vision(self, status=200, body=None, content=b"", ctype="application/json"):
        async def fake(method, path, content=None, params=None, timeout=10.0):
            self.calls.append((method, path, content, params))
            if ctype == "application/json":
                return httpx.Response(status, json=body if body is not None else {})
            return httpx.Response(status, content=reply, headers={"content-type": ctype})
        reply = content
        return mock.patch.object(setup_face, "_vision", new=fake)

    def test_context_tells_server_from_remote(self):
        self.assertEqual(self.client.get("/api/setup/face/context").json()["mode"], "server")
        self.local = False
        body = self.client.get("/api/setup/face/context").json()
        self.assertEqual((body["mode"], body["kinds"]), ("remote", ["front", "three_left", "three_right"]))

    def test_browser_frames_are_checked_before_reaching_vision(self):
        with self.vision(body={"face": True}):
            r = self.client.post("/api/setup/face/analyze", content=b"x", headers={**HEADERS, "Content-Type": "text/plain"})
            self.assertEqual(r.status_code, 415)
            big = b"0" * (setup_face.MAX_FRAME + 1)
            r = self.client.post("/api/setup/face/analyze", content=big, headers={**HEADERS, "Content-Type": "image/jpeg"})
            self.assertEqual(r.status_code, 413)
            r = self.client.post("/api/setup/face/analyze", content=FRAME, headers={**HEADERS, "Content-Type": "image/jpeg"})
            self.assertEqual((r.status_code, r.json()), (200, {"face": True}))
            r = self.client.post("/api/setup/face/analyze", content=FRAME, headers={"Content-Type": "image/jpeg"})
            self.assertEqual(r.status_code, 403)
        self.assertEqual([(c[0], c[1], c[2]) for c in self.calls], [("POST", "/setup/analyze", FRAME)])

    def test_server_preview_and_analysis_are_relayed(self):
        with self.vision(content=b"\xff\xd8jpeg", ctype="image/jpeg"):
            r = self.client.get("/api/setup/face/preview.jpg")
        self.assertEqual((r.status_code, r.headers["content-type"]), (200, "image/jpeg"))
        with self.vision(status=503, content=b"", ctype="text/plain"):
            self.assertEqual(self.client.get("/api/setup/face/preview.jpg").status_code, 503)
        with self.vision(status=404, body={"detail": "x"}):
            self.assertEqual(self.client.get("/api/setup/face/analyze").status_code, 503)

    def test_a_browser_shot_is_saved_as_a_view_of_the_owner(self):
        with self.vision(body={"quality": {"score": 88}}):
            r = self.client.post("/api/setup/face?kind=three_left", content=FRAME, headers={**HEADERS, "Content-Type": "image/jpeg"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.json()["source"], r.json()["views"]), ("browser", ["three_left"]))
        method, path, content, params = self.calls[-1]
        self.assertEqual((method, path, content, params["kind"]), ("POST", "/people/nunzio-aprile/views", FRAME, "three_left"))
        with self.vision(body={}):
            r = self.client.post("/api/setup/face?kind=front", headers=HEADERS)
        self.assertEqual(r.json()["views"], ["front", "three_left"])
        self.assertEqual(self.calls[-1][1], "/people/nunzio-aprile/views/capture")

    def test_bad_kind_and_vision_errors(self):
        self.assertEqual(self.client.post("/api/setup/face?kind=back", headers=HEADERS).status_code, 400)
        with self.vision(status=422, body={"detail": "Foto non adatta"}):
            r = self.client.post("/api/setup/face?kind=front", content=FRAME, headers={**HEADERS, "Content-Type": "image/jpeg"})
        self.assertEqual((r.status_code, r.json()["detail"]), (422, "Foto non adatta"))
        with self.vision(status=503, body={}):
            self.assertEqual(self.client.post("/api/setup/face?kind=front", headers=HEADERS).status_code, 503)
        self.assertEqual(session_manager.config.get("face_views") or [], [])


if __name__ == "__main__":
    unittest.main()
