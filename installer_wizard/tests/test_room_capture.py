import unittest

from agenti.ear.room_capture import RoomCapture


class RoomCaptureTests(unittest.TestCase):
    def test_same_words_from_distinct_captures_are_deduplicated_in_one_room(self):
        captures = RoomCapture()
        display, satellite = object(), object()
        self.assertTrue(captures.accepts("office", display, "Apri il progetto!", 10))
        self.assertFalse(captures.accepts("office", satellite, "APRI IL PROGETTO", 10.5))
        self.assertTrue(captures.accepts("kitchen", satellite, "Apri il progetto", 10.5))
        self.assertTrue(captures.accepts("office", satellite, "Chiudi il progetto", 10.6))
        self.assertTrue(captures.accepts("office", satellite, "Apri il progetto", 12))

    def test_same_device_can_repeat_a_command(self):
        captures = RoomCapture()
        display = object()
        self.assertTrue(captures.accepts("office", display, "Ripeti", 10))
        self.assertTrue(captures.accepts("office", display, "Ripeti", 10.5))
