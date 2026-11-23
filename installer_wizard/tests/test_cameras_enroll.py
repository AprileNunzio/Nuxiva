import unittest

from agenti.cameras import enroll
from agenti.vision import devices as dev

WEBCAM = {"id": "046d:0825@usb-0000:00:14.0-6", "name": "Logitech C270", "rgb": "/dev/video2", "ir": None, "meta": ["/dev/video3"]}
MAIN = {"id": "0bda:5634@usb-0000:00:14.0-8", "name": "Integrated", "rgb": "/dev/video0", "ir": "/dev/video4", "meta": []}


class EnrollPlanTest(unittest.TestCase):
    def test_new_webcam_is_added_once_with_stable_id(self):
        actions = enroll.plan([WEBCAM, MAIN], {}, {"/dev/video0", "/dev/video4"})
        self.assertEqual(len(actions["add"]), 1)
        self.assertEqual(actions["add"][0]["device_id"], WEBCAM["id"])
        self.assertEqual(actions["add"][0]["url"], "/dev/video2")

    def test_renumbered_node_updates_instead_of_duplicating(self):
        items = {"a1": {"id": "a1", "kind": "webcam", "url": "/dev/video1", "node": "/dev/video1", "device_id": WEBCAM["id"], "created": 1}}
        actions = enroll.plan([WEBCAM], items, set())
        self.assertEqual(actions["add"], [])
        self.assertEqual(actions["update"], [("a1", {"device_id": WEBCAM["id"], "url": "/dev/video2", "node": "/dev/video2"})])

    def test_duplicates_of_one_physical_camera_are_merged(self):
        items = {"a1": {"id": "a1", "kind": "webcam", "url": "/dev/video2", "node": "/dev/video2", "created": 1},
                 "b2": {"id": "b2", "kind": "webcam", "url": "/dev/video3", "node": "/dev/video3", "created": 2},
                 "c3": {"id": "c3", "kind": "rtsp", "url": "rtsp://cam", "created": 3}}
        actions = enroll.plan([WEBCAM], items, set())
        self.assertEqual(actions["remove"], ["b2"])
        self.assertEqual(actions["update"][0][0], "a1")

    def test_vision_camera_is_not_enrolled_and_reports_busy(self):
        actions = enroll.plan([MAIN], {}, {"/dev/video0"})
        self.assertEqual(actions["add"], [])
        self.assertEqual(enroll.busy_reason({"kind": "webcam", "url": "/dev/video0"}, {"/dev/video0"}), "in_use_by_vision")
        self.assertEqual(enroll.busy_reason({"kind": "rtsp", "url": "rtsp://x"}, {"/dev/video0"}), "")

    def test_invalid_device_id_is_ignored(self):
        self.assertEqual(enroll.plan([{**WEBCAM, "id": "../../etc"}], {}, set())["add"], [])


class SameBusTest(unittest.TestCase):
    def test_one_usb_camera_with_two_headers_is_one_group(self):
        text = ("Integrated Camera: Integrated C (usb-0000:00:14.0-8):\n\t/dev/video0\n\t/dev/video1\n"
                "Integrated Camera: Integrated I (usb-0000:00:14.0-8):\n\t/dev/video2\n\t/dev/video3\n"
                "bcm2835-isp (platform:bcm2835-isp):\n\t/dev/video13\n")
        groups = dev.parse_list(text)
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0]["nodes"], ["/dev/video0", "/dev/video1", "/dev/video2", "/dev/video3"])


if __name__ == "__main__":
    unittest.main()
