import unittest
from unittest import mock

from agenti.people import percept
from tests.test_context_hot import HotContextBase
from tests.test_percept_native import NATIVE


@unittest.skipUnless(NATIVE, "modulo nativo non installato")
class PerceptFeedTest(HotContextBase):
    def setUp(self):
        super().setUp()
        percept.reset()
        self.addCleanup(percept.reset)
        self.family()

    def test_each_sensor_reaches_the_fusion(self):
        seen = []
        real = percept._send
        percept._send = lambda observation, now: (seen.append(observation["kind"]), real(observation, now))[1]
        self.addCleanup(setattr, percept, "_send", real)
        percept.note_speaker("anna", 0.9)
        percept.note_people(["anna"])
        percept.note_scene("scene-abc123")
        percept.note_mood("anna", "felice", 4, "umore")
        self.assertEqual(sorted(seen), ["emotion", "presence", "scene", "speaker"])

    def test_empty_scene_and_unknown_mood_are_ignored(self):
        with mock.patch.object(percept, "_send") as send:
            percept.note_scene(None)
            percept.note_scene("")
            percept.note_mood("anna", "inesistente", 3, "umore")
            send.assert_not_called()

    def test_failures_are_logged_not_raised(self):
        with mock.patch.object(percept, "_send", side_effect=ValueError("x")), self.assertLogs("nuxiva.people.percept", "ERROR"):
            percept.note_speaker("anna", 0.9)

    def test_mood_axes_are_scaled_and_bounded(self):
        captured = []
        with mock.patch.object(percept, "_send", side_effect=lambda o, n: captured.append(o)):
            percept.note_mood("anna", "arrabbiato", 5, "umore")
            percept.note_mood("anna", "felice", 99, "umore")
        self.assertEqual(captured[0]["valence"], -700)
        self.assertEqual(captured[0]["arousal"], 900)
        self.assertEqual(captured[1]["valence"], 800)

    def test_disabled_when_native_missing(self):
        with mock.patch.object(percept, "_native", return_value=None), mock.patch.object(percept, "_send") as send:
            percept.note_speaker("anna", 1.0)
            send.assert_not_called()
