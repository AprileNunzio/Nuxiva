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
import stt
import vocabulary


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
            "piano_terra": {"name": "Piano terra"}
        }

        fake_store = mock.Mock()
        room = mock.Mock()
        room.name = "Mansarda"
        room.aliases = ["Soffitta"]
        fake_store.rooms = {"r1": room}
        fake_store.floors = {}

        with mock.patch("features.home_assistant.home.brain.catalog", fake_catalog), \
             mock.patch("features.places.store.store", fake_store), \
             mock.patch.object(vocabulary, "_collect_family_names", return_value=["Marco", "Anna"]):
            words = vocabulary.home_vocabulary_list(limit=20)
            words_str = vocabulary.home_vocabulary_string(limit=20)

        self.assertIn("Nuxiva", words)
        self.assertIn("Marco", words)
        self.assertIn("Anna", words)
        self.assertIn("Veletta", words)
        self.assertIn("Salotto", words)
        self.assertIn("Mansarda", words)
        self.assertIn("Veletta", words_str)

    def test_transcribe_gemini_injects_vocabulary_in_prompt_and_uses_model(self):
        captured = {}

        def fake_urlopen(req, timeout):
            captured["url"] = req.full_url
            captured["data"] = json.loads(req.data.decode("utf-8"))
            captured["timeout"] = timeout
            return DummyResponse(json.dumps({
                "candidates": [{
                    "content": {"parts": [{"text": "accendi led veletta"}]}
                }]
            }).encode("utf-8"))

        with mock.patch.object(online_stt.urllib.request, "urlopen", side_effect=fake_urlopen), \
             mock.patch.object(vocabulary, "home_vocabulary_string", return_value="Veletta, Salotto"), \
             mock.patch.dict(os.environ, {"NUXIVA_ONLINE_STT_MODEL": "gemini-3.5-flash"}):
            text = online_stt.transcribe_gemini(_dummy_wav(), api_key="secret123", lang="it")

        self.assertEqual(text, "accendi led veletta")
        self.assertIn("gemini-3.5-flash", captured["url"])
        parts = captured["data"]["contents"][0]["parts"]
        prompt_text = parts[0]["text"]
        self.assertIn("Veletta", prompt_text)
        self.assertIn("Salotto", prompt_text)
        self.assertEqual(parts[1]["inline_data"]["mime_type"], "audio/wav")

    def test_transcribe_openai_compatible_injects_prompt_field(self):
        captured = {}

        def fake_urlopen(req, timeout):
            captured["url"] = req.full_url
            captured["data"] = req.data.decode("utf-8", errors="replace")
            captured["timeout"] = timeout
            return DummyResponse(json.dumps({"text": "accendi led veletta"}).encode("utf-8"))

        with mock.patch.object(online_stt.urllib.request, "urlopen", side_effect=fake_urlopen), \
             mock.patch.object(vocabulary, "home_vocabulary_string", return_value="Veletta, Salotto"):
            text = online_stt.transcribe_openai_compatible(
                _dummy_wav(),
                endpoint="https://api.groq.com/openai/v1/audio/transcriptions",
                model="whisper-large-v3-turbo",
                api_key="gkey",
                lang="it"
            )

        self.assertEqual(text, "accendi led veletta")
        self.assertIn("name=\"prompt\"", captured["data"])
        self.assertIn("Veletta", captured["data"])

    def test_transcribe_deepgram_includes_keywords_param(self):
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
            hw = stt._hotwords("it")

        self.assertIn("Veletta", hw)
        self.assertIn("Salotto", hw)


if __name__ == "__main__":
    unittest.main()
