import unittest
from unittest import mock

from features.sentinel.collectors.voice import record_voice


class SentinelVoiceTest(unittest.TestCase):
    @mock.patch("features.sentinel.collectors.voice.record")
    def test_record_recognized_voice_event(self, mock_record):
        mock_record.return_value = "ev_123"
        ev_id = record_voice("Nuxiva, come va", speaker_slug="Marco", recognized=True, place="salotto")
        self.assertEqual(ev_id, "ev_123")
        mock_record.assert_called_once()
        args, kwargs = mock_record.call_args
        self.assertEqual(kwargs["kind"], "voice.recognized")
        self.assertEqual(kwargs["params"]["person"], "Marco")
        self.assertEqual(kwargs["params"]["phrase"], "Nuxiva, come va")
        self.assertEqual(kwargs["place"], "salotto")

    @mock.patch("features.sentinel.collectors.voice.record")
    def test_record_unknown_voice_event(self, mock_record):
        mock_record.return_value = "ev_456"
        ev_id = record_voice("Qualcuno mi sente?", speaker_slug=None, recognized=False)
        self.assertEqual(ev_id, "ev_456")
        mock_record.assert_called_once()
        args, kwargs = mock_record.call_args
        self.assertEqual(kwargs["kind"], "voice.unknown")
        self.assertEqual(kwargs["params"]["person"], "sconosciuto")

    def test_empty_phrase_returns_none(self):
        res = record_voice("")
        self.assertIsNone(res)
