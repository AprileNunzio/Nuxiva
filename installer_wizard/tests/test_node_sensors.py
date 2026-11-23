import base64
import json
import sys
import types
import unittest
from unittest import mock

import httpx
import numpy as np
from fastapi.responses import JSONResponse

import tests.test_node_trust_api as base
from agenti.nodes import sensor_routes
from agenti.nodes.registry import TYPES

FRAME = b"\xff\xd8\xff\xe0" + b"\x00" * 64


class Reply:
    def __init__(self, status):
        self.status_code = status


class NodeSensorTest(base.TrustApiTest):
    def setUp(self):
        super().setUp()
        sensor_routes.frames.last.clear()
        self.core = mock.AsyncMock(return_value=Reply(200))
        patcher = mock.patch.object(sensor_routes.core, "request", self.core)
        patcher.start()
        self.addCleanup(patcher.stop)

    def ready(self, scopes=("camera.stream", "audio.capture")):
        self.pair()
        self.assertEqual(self.heartbeat(self.device, list(scopes)).status_code, 200)

    def frame(self, data=FRAME):
        return {"frame": base64.b64encode(data).decode()}

    def test_ios_is_a_known_node_type(self):
        self.assertIn("ios", TYPES)

    def test_signed_frame_reaches_the_core_with_the_node_identity(self):
        self.ready()
        reply = self.post(self.device, "/api/nodes/vision/feed", self.frame())
        self.assertEqual(reply.status_code, 200, reply.text)
        sent = self.core.await_args.kwargs["json"]
        self.assertEqual(sent["device_id"], self.device.id)
        self.assertEqual(base64.b64decode(sent["frame_base64"]), FRAME)

    def test_unsigned_frame_is_refused_even_with_a_valid_token(self):
        self.ready()
        body = json.dumps(self.frame()).encode()
        headers = {"content-type": "application/json", "x-nuxiva-node": self.device.id,
                   "authorization": f"Bearer {self.device.token}"}
        reply = self.client.post("/api/nodes/vision/feed", content=body, headers=headers)
        self.assertEqual(reply.status_code, 401)
        self.core.assert_not_awaited()

    def test_frame_without_the_camera_scope_is_forbidden(self):
        self.ready(("audio.capture",))
        self.assertEqual(self.post(self.device, "/api/nodes/vision/feed", self.frame()).status_code, 403)

    def test_non_jpeg_and_bad_base64_are_rejected(self):
        self.ready()
        self.assertEqual(self.post(self.device, "/api/nodes/vision/feed", self.frame(b"GIF89a")).status_code, 415)
        self.assertEqual(self.post(self.device, "/api/nodes/vision/feed", {"frame": "%%%"}).status_code, 400)

    def test_frames_too_close_together_are_rate_limited(self):
        self.ready()
        self.assertEqual(self.post(self.device, "/api/nodes/vision/feed", self.frame()).status_code, 200)
        self.assertEqual(self.post(self.device, "/api/nodes/vision/feed", self.frame()).status_code, 429)

    def test_core_failure_is_reported_not_hidden(self):
        self.ready()
        self.core.side_effect = httpx.ConnectError("down")
        reply = self.post(self.device, "/api/nodes/vision/feed", self.frame())
        self.assertEqual((reply.status_code, reply.json()["detail"]), (502, "core_unavailable"))

    def test_voice_is_transcribed_and_answered(self):
        self.ready()
        stt = types.SimpleNamespace(transcribe=mock.Mock(return_value=("accendi la luce", "it")))
        chat = mock.AsyncMock(return_value=JSONResponse({"speech": "fatto"}))
        pcm = (np.zeros(1600, dtype="<i2")).tobytes()
        with mock.patch.dict(sys.modules, {"agenti.ear.stt": stt}), \
                mock.patch("agenti.ear.stt", stt, create=True), \
                mock.patch("agenti.chat.api.assistant_chat", chat):
            reply = self.post(self.device, "/api/nodes/voice", {"rate": 16000, "pcm16": base64.b64encode(pcm).decode()})
        self.assertEqual(reply.status_code, 200, reply.text)
        self.assertEqual(chat.await_args.args[:2], ("accendi la luce", self.device.id))

    def test_voice_with_wrong_rate_or_odd_length_is_rejected(self):
        self.ready()
        good = base64.b64encode(b"\x00\x00").decode()
        self.assertEqual(self.post(self.device, "/api/nodes/voice", {"rate": 8000, "pcm16": good}).status_code, 400)
        odd = base64.b64encode(b"\x00\x00\x00").decode()
        self.assertEqual(self.post(self.device, "/api/nodes/voice", {"rate": 16000, "pcm16": odd}).status_code, 400)

    def test_pcm_conversion_is_normalised(self):
        audio = sensor_routes.pcm_to_float(np.array([16384, -32768], dtype="<i2").tobytes())
        self.assertEqual(audio.tolist(), [0.5, -1.0])


if __name__ == "__main__":
    unittest.main()
