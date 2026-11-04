import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "features" / "vision"))

import ircam


class GateTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        wake = Path(self.tmp.name) / "ir_wake"
        patch = mock.patch.object(ircam, "WAKE_FILE", wake)
        patch.start()
        self.addCleanup(patch.stop)
        self.wake_file = wake
        with mock.patch.object(ircam.threading, "Thread"):
            self.cam = ircam.IrCamera()
        self.cam.retarget("/dev/video2", None)

    def test_asleep_without_a_person(self):
        self.assertTrue(self.cam.asleep())
        self.assertEqual(self.cam.view()["state"], "idle")

    def test_wake_keeps_it_open_for_the_hold_time(self):
        self.cam.wake(5)
        self.assertFalse(self.cam.asleep())
        self.cam.awake_until = time.time() - 1
        self.assertTrue(self.cam.asleep())

    def test_wake_file_from_another_process_keeps_it_open(self):
        self.wake_file.touch()
        self.assertFalse(self.cam.asleep())
        old = time.time() - ircam.HOLD_SECONDS - 5
        os.utime(self.wake_file, (old, old))
        self.assertTrue(self.cam.asleep())

    def test_gate_can_be_disabled(self):
        with mock.patch.dict(os.environ, {"NUXIVA_IR_GATE": "off"}):
            self.assertFalse(self.cam.asleep())

    def test_status_reports_idle_before_other_states(self):
        self.assertEqual(ircam.status_of(0.0, 0, False, True), "idle")
        self.assertEqual(ircam.status_of(0.0, 5, True, False), "dark")


if __name__ == "__main__":
    unittest.main()
