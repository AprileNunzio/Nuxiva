import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

VISION = Path(__file__).resolve().parents[1] / "features" / "vision"
if str(VISION) not in sys.path:
    sys.path.insert(0, str(VISION))

import learning  # noqa: E402


class SetupGuardTest(unittest.TestCase):
    def test_setup_session_file_controls_the_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "setup_session.json"
            with mock.patch.object(learning, "SETUP_SESSION", marker):
                self.assertFalse(learning.setup_running())
                marker.write_text("{}")
                self.assertTrue(learning.setup_running())

    def test_no_guest_is_created_while_setup_runs(self):
        gallery = mock.Mock()
        vision = SimpleNamespace(enroll_request=None, fusion=SimpleNamespace(active=False), size=(640, 480), tracks=[], gallery=gallery)
        track = SimpleNamespace(echo_of=None, ambiguous=False, live_state="live", box=(0, 0, 200, 200), ir_feature=None,
                                first_seen=0.0, samples=[np.ones(4)] * 20, ir_samples=[], identity=lambda: (None, "", 0.0))
        vision.tracks = [track]
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "setup_session.json"
            marker.write_text("{}")
            with mock.patch.object(learning, "SETUP_SESSION", marker):
                learning.learn(vision, track, None, np.ones(4))
        gallery.next_guest_name.assert_not_called()
        gallery.save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
