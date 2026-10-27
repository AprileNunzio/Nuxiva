import importlib.util
import io
import json
import os
import sys
import unittest
import wave
from pathlib import Path
from unittest import mock

import numpy as np

EAR = Path(__file__).resolve().parents[1] / "features" / "ear"
if str(EAR) not in sys.path:
    sys.path.insert(0, str(EAR))

import online_stt
import vocabulary

_spec = importlib.util.spec_from_file_location("features_ear_stt", EAR / "stt.py")
stt_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stt_module)


class DummyResponse:
    def __init__(self, data: bytes):
        self._data = data

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _dummy_wav() -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(np.zeros(1600, dtype=np.int16).tobytes())
    return buf.getvalue()


class EarVocabularySttTest(unittest.TestCase):
    def setUp(self):
        vocabulary.invalidate_cache()
        self.addCleanup(vocabulary.invalidate_cache)

    def test_vocabulary_aggregates_devices_areas_and_people(self):
        fake_catalog = mock.Mock()
        fake_catalog.entities = {
            "light.veletta": {"name": "LED Veletta", "domain": "light"},
            "switch.clima": {"name": "Condizionatore", "domain": "climate"}
        }
        fake_catalog.areas = {
            "salotto": {"name": "Salotto"},
            "cucina": {"name": "Cucina"}
        }
        fake_catalog.floors = {
            "zona_notte": {"name": "Zona Notte"}
        }

        fake_places = mock.Mock()
        fake_places.rooms = [
            {"id": "r1", "name": "Studio Tecnico"}
        ]
        fake_places.floors = [
            {"id": "f1", "name": "Primo Piano"}
        ]

        fake_learner = mock.Mock()
        fake_learner.hotwords.return_value = ["Nuxiva", "Marco"]

        with mock.patch("vocabulary._get_brain_catalog", return_value=fake_catalog), \
             mock.patch("vocabulary._get_places_store", return_value=fake_places), \
             mock.patch("vocabulary._get_learner", return_value=fake_learner):
            voc = vocabulary.home_vocabulary_list("it")

        self.assertIn("Nuxiva", voc)
        self.assertIn("Marco", voc)
        self.assertIn("LED Veletta", voc)
        self.assertIn("Condizionatore", voc)
        self.assertIn("Salotto", voc)
        self.assertIn("Cucina", voc)
        self.assertIn("Zona Notte", voc)
        self.assertIn("Studio Tecnico", voc)
        self.assertIn("Primo Piano", voc)

    def test_gemini_prompt_contains_context_vocabulary(self):
        with mock.patch.object(vocabulary, "home_vocabulary_list", return_value=["Nuxiva", "Veletta", "Salotto"]):
            prompt = vocabulary.gemini_prompt("it")

        self.assertIn("Veletta", prompt)
        self.assertIn("Salotto", prompt)
        self.assertIn("Nuxiva", prompt)

    def test_transcribe_gemini_injects_vocabulary_prompt(self):
        captured = {}

        def fake_urlopen(req, timeout):
            captured["url"] = req.full_url
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return DummyResponse(json.dumps({
                "candidates": [{
                    "content": {
                        "parts": [{"text": "accendi led veletta in salotto"}]
                    }
                }]
            }).encode("utf-8"))

        with mock.patch.object(online_stt.urllib.request, "urlopen", side_effect=fake_urlopen), \
             mock.patch.object(vocabulary, "home_vocabulary_list", return_value=["Veletta", "Salotto"]), \
             mock.patch.dict(os.environ, {"NUXIVA_ONLINE_STT_MODEL": "gemini-3.5-flash"}):
            text = online_stt.transcribe_gemini(_dummy_wav(), api_key="secret123", lang="it")

        self.assertEqual(text, "accendi led veletta in salotto")
        self.assertIn("models/gemini-3.5-flash:generateContent", captured["url"])
        parts = captured["body"]["contents"][0]["parts"]
        text_parts = [p.get("text", "") for p in parts if "text" in p]
        self.assertTrue(any("Veletta" in t for t in text_parts))

    def test_transcribe_openai_compatible_injects_prompt(self):
        captured = {}

        def fake_urlopen(req, timeout):
            captured["body"] = req.data
            return DummyResponse(json.dumps({
                "text": "accendi led veletta"
            }).encode("utf-8"))

        with mock.patch.object(online_stt.urllib.request, "urlopen", side_effect=fake_urlopen), \
             mock.patch.object(vocabulary, "home_vocabulary_list", return_value=["Veletta", "Salotto"]):
            text = online_stt.transcribe_openai_compatible(
                _dummy_wav(),
                endpoint="https://api.groq.com/openai/v1",
                api_key="gkey",
                model="whisper-large-v3",
                lang="it"
            )

        self.assertEqual(text, "accendi led veletta")
        body_str = captured["body"].decode("utf-8", errors="replace")
        self.assertIn('name="prompt"', body_str)
        self.assertIn("Veletta", body_str)

    def test_transcribe_deepgram_injects_keywords(self):
        captured = {}

        def fake_urlopen(req, timeout):
            captured["url"] = req.full_url
            return DummyResponse(json.dumps({
                "results": {"channels": [{"alternatives": [{"transcript": "accendi led veletta"}]}]}
            }).encode("utf-8"))

        with mock.patch.object(online_stt.urllib.request, "urlopen", side_effect=fake_urlopen), \
             mock.patch.object(vocabulary, "deepgram_keywords", return_value=["Veletta", "Salotto"]):
            text = online_stt.transcribe_deepgram(_dummy_wav(), lang="it", api_key="dkey")

        self.assertEqual(text, "accendi led veletta")
        self.assertIn("&keywords=Veletta", captured["url"])
        self.assertIn("&keywords=Salotto", captured["url"])

    def test_stt_hotwords_includes_home_vocabulary(self):
        with mock.patch.object(vocabulary, "home_vocabulary_list", return_value=["Nuxiva", "Veletta", "Salotto"]):
            hw = stt_module._hotwords("it")

        self.assertIn("Veletta", hw)
        self.assertIn("Salotto", hw)


if __name__ == "__main__":
    unittest.main()
