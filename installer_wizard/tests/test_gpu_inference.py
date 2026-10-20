import importlib.util
import types
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("nuxiva_gpu_inference", ROOT / "docker/inference/inference_service.py")
service = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(service)


class GpuInferenceTest(unittest.TestCase):
    def setUp(self):
        self.http = TestClient(service.app)

    def test_health_does_not_load_or_download_models(self):
        with mock.patch.object(service, "_model", None):
            self.assertEqual(self.http.get("/health").json(), {"status": "ok", "model_loaded": False})

    def test_transcription_returns_text_and_removes_temporary_audio(self):
        paths = []

        def transcribe(path, **kwargs):
            paths.append(Path(path))
            self.assertEqual(Path(path).read_bytes(), b"audio")
            return [types.SimpleNamespace(text=" ciao ")], types.SimpleNamespace(language="it", language_probability=0.99)

        model = mock.Mock()
        model.transcribe.side_effect = transcribe
        with mock.patch.object(service, "_model", model):
            response = self.http.post("/transcribe", files={"file": ("sample.wav", b"audio")})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["text"], "ciao")
        self.assertTrue(paths)
        self.assertFalse(paths[0].exists())

    def test_invalid_and_oversized_audio_are_rejected(self):
        self.assertEqual(self.http.post("/transcribe", files={"file": ("empty.wav", b"")}).status_code, 400)
        with mock.patch.object(service, "MAX_AUDIO_BYTES", 3):
            self.assertEqual(self.http.post("/transcribe", files={"file": ("big.wav", b"audio")}).status_code, 413)

    def test_decoder_failure_cleans_up_audio(self):
        model = mock.Mock()
        paths = []

        def fail(path, **kwargs):
            paths.append(Path(path))
            raise ValueError("invalid audio")

        model.transcribe.side_effect = fail
        with mock.patch.object(service, "_model", model):
            response = self.http.post("/transcribe", files={"file": ("sample.wav", b"broken")})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(paths[0].exists())
